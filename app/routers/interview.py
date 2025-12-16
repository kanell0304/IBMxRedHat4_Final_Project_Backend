from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from app.database.database import get_db
from app.service.analysis_service import get_analysis_service
from app.service.i_start_service import i_start_session
from app.database.schemas.interview import AnalyzeReq, I_Report, ProcessAnswerResponse, AnswerUploadResponse, I_Create, I_Basic, I_Detail, AnswerCreate, Answer, I_Result, I_StartReq, I_StartRes, AnswerUploadProcessResponse
from app.database.crud import interview as crud
from app.service.i_stats_service import compute_interview_stt_metrics
from app.service.llm_service import OpenAIService
from app.service.answer_analysis_service import i_process_answer, analyze_weakness_patterns, analyze_speech_style_evolution, extract_transcript, aggregate_bert_labels
from app.service.audio_service import AudioService
from app.service.stt_service import STTService
from app.service.i_stt_metrics import compute_stt_metrics
from app.core.settings import settings


router=APIRouter(prefix="/interview", tags=["interview"])

# DB 질문 기반 인터뷰 시작
@router.post("/start", response_model=I_StartRes)
async def i_start(payload: I_StartReq, db = Depends(get_db)):
    return await i_start_session(db, payload)


# 대화 전체 분석
@router.post("/analyze", response_model=I_Report)
async def analyze(request:AnalyzeReq, db=Depends(get_db)):
    interview=await crud.get_i(db, request.i_id)    
    service=get_analysis_service()
    report=await service.analyze_interview(request.transcript)

    await crud.create_result(db=db, user_id=interview.user_id, i_id=request.i_id, scope="overall", report=report.model_dump())
    return report


# 인터뷰 전체 종합 분석
@router.post("/{i_id}/analyze_full", response_model=I_Report)
async def analyze_interview_full(i_id:int, db=Depends(get_db)):
    try:
        interview=await crud.get_i(db, i_id)
        if not interview:
            raise HTTPException(status_code=404, detail="모의면접을 찾을 수 없습니다.")
        
        answers=interview.answers
        if not answers:
            raise HTTPException(status_code=400, detail="답변이 없습니다.")
        
        transcripts=[]
        bert_labels_list=[]
        qa_list=[]

        for answer in answers:
            if not answer.transcript:
                continue

            transcripts.append(answer.transcript)

            if answer.labels_json:
                bert_labels_list.append(answer.labels_json.get("overall_labels", {}))

            question=await crud.get_question(db, answer.q_id) if answer.q_id else None
            qa_list.append({
                "question":question.question_text if question else "",
                "answer":answer.transcript,
                "q_id":answer.q_id,
                "answer_id":answer.i_answer_id
            })
        
        if not transcripts:
            raise HTTPException(status_code=400, detail="처리된 답변이 없습니다.")
        full_transcript=" ".join(transcripts)

        bert_analysis=aggregate_bert_labels(bert_labels_list)

        stt_metrics=await compute_interview_stt_metrics(i_id, db)

        weakness_patterns=analyze_weakness_patterns(interview.user_id)
        evolution_insights=analyze_speech_style_evolution(interview.user_id)

        llm_service=OpenAIService()
        report=await llm_service.generate_report(
            transcript=full_transcript,
            bert_analysis=bert_analysis,
            stt_metrics=stt_metrics,
            weakness_pattern=weakness_patterns,
            evolution_insights=evolution_insights,
            qa_list=qa_list
        )

        # 전체 결과 저장
        await crud.create_result(
            db=db,
            user_id=interview.user_id,
            i_id=i_id,
            scope="overall",
            report=report.model_dump()
        )

        # 질문별 개별 결과 저장
        if report.content_per_question:
            for per_q in report.content_per_question:
                q_index=per_q.q_index

                if 0<q_index<=len(qa_list):
                    qa_item=qa_list[q_index-1]
                    q_id=qa_item.get("q_id")
                    answer_id=qa_item.get("answer_id")

                    per_question_report={
                        "q_index":per_q.q_index,
                        "q_text":per_q.q_text,
                        "score":per_q.score,
                        "comment":per_q.comment,
                        "suggestion":per_q.suggestion,
                    }

                    await crud.create_result(
                        db=db,
                        user_id=interview.user_id,
                        i_id=i_id,
                        scope="per_question",
                        report=per_question_report,
                        i_answer_id=answer_id,
                        q_id=q_id,
                    )

        await crud.update_interview(db, i_id, status=2)

        return report
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 : {e}")


@router.get("/answers/{answer_id}/result", response_model=dict)
async def get_answer_result(answer_id:int, db=Depends(get_db)):
    from sqlalchemy import select
    from app.database.models.interview import InterviewResult

    result=await db.execute(
        select(InterviewResult).where(
            InterviewResult.i_answer_id==answer_id,
            InterviewResult.scope=="per_question")
    )
    per_q_result=result.scalar_one_or_none()

    if not per_q_result:
        raise HTTPException(status_code=404, detail="해당 답변의 결과를 찾을 수 없습니다.")

    return per_q_result.report


# 개별 답변 라벨링/문장 분해 처리
@router.post("/answers/{answer_id}/process", response_model=ProcessAnswerResponse)
async def process_answer(answer_id: int, db = Depends(get_db)):
    return await i_process_answer(answer_id, db)


# 답변 오디오 업로드
@router.post("/answers/{answer_id}/upload", response_model=AnswerUploadResponse)
async def upload_answer_audio(answer_id: int, file: UploadFile = File(...), db = Depends(get_db)):
    answer = await crud.get_answer(db, answer_id)

    data = await file.read()
    ext = (file.filename.split(".")[-1] if "." in file.filename else "wav") or "wav"

    wav_data, duration = AudioService.convert_to_wav(data, ext)
    stt_service = STTService(project_id=settings.google_cloud_project_id)
    stt_result = await stt_service.transcribe_chirp(wav_data)
    transcript = extract_transcript(stt_result)
    stt_metrics = compute_stt_metrics(stt_result)

    answer.transcript = transcript
    answer.duration_sec = int(round(duration)) if duration is not None else None
    answer.stt_metrics_json = stt_metrics
    await db.commit()
    await db.refresh(answer)

    return AnswerUploadResponse(
        answer_id=answer_id,
        audio_format=ext,
        size=len(data),
        transcript=transcript,
        duration_sec=answer.duration_sec,
        stt_metrics=stt_metrics,
    )

# 답변 오디오 업로드 + BERT 분석 통합
@router.post("/answers/{answer_id}/upload_process", response_model=AnswerUploadProcessResponse)
async def upload_process_answer_audio(answer_id:int, file:UploadFile=File(...), db=Depends(get_db)):
    answer=await crud.get_answer(db, answer_id)

    data=await file.read()
    ext=(file.filename.split(".")[-1] if "." in file.filename else "wav") or "wav"

    # STT 처리
    wav_data, duration=AudioService.convert_to_wav(data, ext)
    stt_service=STTService(project_id=settings.google_cloud_project_id)
    stt_result=await stt_service.transcribe_chirp(wav_data)
    transcript=extract_transcript(stt_result)
    stt_metrics=compute_stt_metrics(stt_result)

    # DB 저장
    answer.transcript=transcript
    answer.duration_sec=int(round(duration)) if duration is not None else None
    answer.stt_metrics_json=stt_metrics
    await db.commit()
    await db.refresh(answer)

    # process
    process_result=await i_process_answer(answer_id, db)

    # 통합 응답 반환
    return AnswerUploadProcessResponse(
        answer_id=answer_id,
        audio_format=ext,
        size=len(data),
        transcript=process_result["transcript"],
        duration_sec=answer.duration_sec,
        stt_metrics=process_result["stt_metrics"],
        bert_analysis={
            "labels": answer.labels_json.get("overall_labels", {}),
            "scores": {}
        },
        sentences=process_result["sentences"],
        label_counts=process_result["label_counts"],
    )

# 인터뷰 생성
@router.post("", response_model=I_Basic)
async def create_i(payload: I_Create, db = Depends(get_db)):
    return await crud.create_i(
        db=db,
        user_id=payload.user_id,
        interview_type=payload.interview_type,
        category_id=payload.category_id,
        total_questions=payload.total_questions,
    )


# 인터뷰 단건 조회
@router.get("/{i_id}", response_model=I_Detail)
async def get_i(i_id: int, db = Depends(get_db)):
    return await crud.get_i(db, i_id)


# 사용자별 인터뷰 목록
@router.get("/users/{user_id}/interviews", response_model=list[I_Basic])
async def list_user_i(user_id: int, db = Depends(get_db)):
    return await crud.list_i(db, user_id)


# 답변 생성/저장
@router.post("/{i_id}/answers", response_model=Answer)
async def create_answer_i(i_id: int, payload: AnswerCreate, db = Depends(get_db)):
    await crud.get_i(db, i_id)

    return await crud.create_answer(
        db=db,
        i_id=i_id,
        q_id=payload.q_id,
        q_order=payload.q_order,
    )


# 답변 삭제
@router.delete("/{i_id}/answers/{answer_id}", status_code=204)
async def delete_answer_i(i_id: int, answer_id: int, db = Depends(get_db)):
    deleted = await crud.delete_answer(answer_id, i_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)


# 인터뷰 완료 처리
@router.post("/{i_id}/complete", response_model=I_Basic)
async def complete_i(i_id: int, db = Depends(get_db)):
    i = await crud.complete_i(db, i_id)
    if not i:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return i


# 인터뷰 결과 조회
@router.get("/{i_id}/results", response_model=list[I_Result])
async def get_results(i_id: int, db = Depends(get_db)):
    return await crud.list_results(db, i_id)


# 인터뷰 삭제
@router.delete("/{i_id}", status_code=204)
async def delete_i(i_id: int, db = Depends(get_db)):
    deleted = await crud.delete_i(db, i_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)