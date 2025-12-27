from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.service.analysis_service import get_analysis_service
from app.service.i_start_service import i_start_session
from app.database.schemas.interview import AnalyzeReq, I_Report, I_Report_En, ProcessAnswerResponse, AnswerUploadResponse, I_Create, I_Basic, I_Detail, AnswerCreate, Answer, I_Result, I_StartReq, I_StartRes, AnswerUploadProcessResponse, ImmediateResultResponse, MetricChangeCardResponse, WeaknessCardResponse
from app.database.crud import interview as crud
from app.service.i_stats_service import compute_interview_stt_metrics
from app.service.llm_service import OpenAIService
from app.service.answer_analysis_service import i_process_answer, extract_transcript, aggregate_bert_labels
from app.service.audio_service import AudioService
from app.service.stt_service import STTService
from app.service.i_stt_metrics import compute_stt_metrics
from app.core.settings import settings



router=APIRouter(prefix="/interview", tags=["interview"])

# DB 질문 기반 인터뷰 시작
@router.post("/start", response_model=I_StartRes)
async def i_start(payload: I_StartReq, db: AsyncSession = Depends(get_db)):
    return await i_start_session(db, payload)


# 대화 전체 분석
@router.post("/analyze", response_model=I_Report)
async def analyze(request:AnalyzeReq, db: AsyncSession = Depends(get_db)):
    interview=await crud.get_i(db, request.i_id)    
    service=get_analysis_service()
    report=await service.analyze_interview(request.transcript)

    await crud.create_result(db=db, user_id=interview.user_id, i_id=request.i_id, scope="overall", report=report.model_dump())
    return report


# 인터뷰 전체 종합 분석
@router.post("/{i_id}/analyze_full")
async def analyze_interview_full(i_id:int, db: AsyncSession = Depends(get_db)):
    try:
        interview=await crud.get_i(db, i_id)
        if not interview:
            raise HTTPException(status_code=404, detail="모의면접을 찾을 수 없습니다.")
        

        language=interview.language
        if language=="en":
            from app.service.i_en_analysis import analyze_english_interview

            answers=interview.answers
            if not answers:
                raise HTTPException(status_code=400, detail="답변이 없습니다.")
            
            transcripts=[]
            qa_list=[]

            for answer in answers:
                if not answer.transcript:
                    continue
                transcripts.append(answer.transcript)

                question=await crud.get_question(db, answer.q_id) if answer.q_id else None
                qa_list.append({
                    "question":question.question_text if question else "",
                    "answer":answer.transcript,
                    "q_id":answer.q_id,
                    "answer_id":answer.i_answer_id,
                })

            if not transcripts:
                raise HTTPException(status_code=400, detail="처리된 답변이 없습니다.")
            
            full_transcript=" ".join(transcripts)

            avg_stt_metrics={
                "speech_rate":0.0,
                "pause_ratio":0.0,
                "filler":{
                    "hard":0,
                    "soft":0
                }
            }

            valid_count=0
            for answer in answers:
                if answer.stt_metrics_json:
                    avg_stt_metrics["speech_rate"]+=answer.stt_metrics_json.get("speech_rate", 0)
                    avg_stt_metrics["pause_ratio"]+=answer.stt_metrics_json.get("pause_ratio", 0)

                    filler_data=answer.stt_metrics_json.get("filler", {})
                    avg_stt_metrics["filler"]["hard"]+=filler_data.get("hard", 0)
                    avg_stt_metrics["filler"]["soft"]+=filler_data.get("soft", 0)
                    valid_count+=1

            if valid_count>0:
                avg_stt_metrics["speech_rate"]=round(avg_stt_metrics["speech_rate"]/valid_count, 2)
                avg_stt_metrics["pause_ratio"]=round(avg_stt_metrics["pause_ratio"]/valid_count, 3)

            analysis_result=await analyze_english_interview(
                transcript=full_transcript,
                stt_metrics=avg_stt_metrics,
                qa_list=qa_list
            )

            report_data={
                "score":analysis_result["score"],
                "grade":analysis_result["grade"],
                "comments":analysis_result["comments"],
                "improvements":analysis_result["improvements"],
                "stt_metrics":analysis_result["stt_metrics"]
            }

            await crud.create_result(
                db=db,
                user_id=interview.user_id,
                i_id=i_id,
                scope="overall",
                report=report_data
            )

            await crud.update_interview(db, i_id, status=2)

            return I_Report_En(
                score=analysis_result["score"],
                grade=analysis_result["grade"],
                comments=analysis_result["comments"],
                improvements=analysis_result["improvements"],
                stt_metrics=analysis_result["stt_metrics"]
            )

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

        llm_service=OpenAIService()
        report=await llm_service.generate_report(
            transcript=full_transcript,
            bert_analysis=bert_analysis,
            stt_metrics=stt_metrics,
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

        await crud.update_interview(db, i_id, status=2)

        return report
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 : {e}")


# 인터뷰 직후 결과
@router.get("/{i_id}/immediate_result", response_model=ImmediateResultResponse)
async def get_interview_immediate_result(i_id: int, db: AsyncSession = Depends(get_db)):
    from app.service.immediate_result_service import get_immediate_result
    try:
        return await get_immediate_result(i_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 조회 중 오류: {e}")


@router.get("/answers/{answer_id}/result", response_model=dict)
async def get_answer_result(answer_id:int, db: AsyncSession = Depends(get_db)):
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
async def process_answer(answer_id: int, db: AsyncSession = Depends(get_db)):
    return await i_process_answer(answer_id, db)


# 답변 오디오 업로드
@router.post("/answers/{answer_id}/upload", response_model=AnswerUploadResponse)
async def upload_answer_audio(answer_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    answer = await crud.get_answer(db, answer_id)


    interview=await crud.get_i(db, answer.i_id)
    language=interview.language

    data = await file.read()
    ext = (file.filename.split(".")[-1] if "." in file.filename else "wav") or "wav"

    wav_data, duration = AudioService.convert_to_wav(data, ext)


    if language=="en":
        from app.service.whisper_stt_service import WhisperSTTService
        from app.service.en_stt_metrics import compute_en_stt_metrics

        stt_service=WhisperSTTService(model_name="base")
        stt_result=await stt_service.transcribe_english(wav_data)
        transcript=extract_transcript(stt_result)
        stt_metrics=compute_en_stt_metrics(stt_result)

    else:
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
async def upload_process_answer_audio(answer_id:int, file:UploadFile=File(...), db: AsyncSession = Depends(get_db)):
    answer=await crud.get_answer(db, answer_id)

    interview=await crud.get_i(db, answer.i_id)
    language=interview.language

    data=await file.read()
    ext=(file.filename.split(".")[-1] if "." in file.filename else "wav") or "wav"

    # STT 처리
    wav_data, duration=AudioService.convert_to_wav(data, ext)

    if language=="en":
        from app.service.whisper_stt_service import WhisperSTTService
        from app.service.en_stt_metrics import compute_en_stt_metrics

        stt_service=WhisperSTTService(model_name="base")
        stt_result=await stt_service.transcribe_english(wav_data)
        transcript=extract_transcript(stt_result)
        stt_metrics=compute_en_stt_metrics(stt_result)
    else:
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


    if language=="en":
        return AnswerUploadProcessResponse(
            answer_id=answer_id,
            audio_format=ext,
            size=len(data),
            transcript=transcript,
            duration_sec=answer.duration_sec,
            stt_metrics=stt_metrics,
            bert_analysis=None,
            sentences=[],
            label_counts={},
        )


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
async def create_i(payload: I_Create, db: AsyncSession = Depends(get_db)):
    return await crud.create_i(
        db=db,
        user_id=payload.user_id,
        interview_type=payload.interview_type,
        category_id=payload.category_id,
        total_questions=payload.total_questions,
    )


# 인터뷰 단건 조회
@router.get("/{i_id}", response_model=I_Detail)
async def get_i(i_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.get_i(db, i_id)


# 사용자별 인터뷰 목록
@router.get("/users/{user_id}/interviews", response_model=list[I_Basic])
async def list_user_i(user_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.list_i(db, user_id)


# 답변 생성/저장
@router.post("/{i_id}/answers", response_model=Answer)
async def create_answer_i(i_id: int, payload: AnswerCreate, db: AsyncSession = Depends(get_db)):
    await crud.get_i(db, i_id)

    return await crud.create_answer(
        db=db,
        i_id=i_id,
        q_id=payload.q_id,
        q_order=payload.q_order,
    )


# 답변 삭제
@router.delete("/{i_id}/answers/{answer_id}", status_code=204)
async def delete_answer_i(i_id: int, answer_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_answer(answer_id, i_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)


# 인터뷰 완료 처리
@router.post("/{i_id}/complete", response_model=I_Basic)
async def complete_i(i_id: int, db: AsyncSession = Depends(get_db)):
    i = await crud.complete_i(db, i_id)
    if not i:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return i


# 인터뷰 결과 조회
@router.get("/{i_id}/results", response_model=list[I_Result])
async def get_results(i_id: int, db: AsyncSession = Depends(get_db)):
    results = await crud.list_results(db, i_id)

    interview = await crud.get_i(db, i_id)
    if not interview:
        raise HTTPException(status_code=404, detail="인터뷰를 찾을 수 없습니다.")

    for result in results:
        if result.scope == "overall" and "content_per_question" in result.report:
            answers = interview.answers
            for per_q in result.report["content_per_question"]:
                matching_answer = next((a for a in answers if a.q_order == per_q["q_index"]), None)
                per_q["user_answer"] = matching_answer.transcript if matching_answer else ""

    return results


# 인터뷰 삭제
@router.delete("/{i_id}", status_code=204)
async def delete_i(i_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_i(db, i_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)


# 히스토리 : 말버릇/약점 분석
@router.get("/users/{user_id}/weaknesses", response_model=WeaknessCardResponse)
async def get_user_weaknesses(
    user_id:int,
    db:AsyncSession=Depends(get_db)
):
    from app.service.weakness_analyzer import get_weakness_analysis
    try:
        return await get_weakness_analysis(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"약점 분석 중 오류: {e}")


# 히스토리 : 지표 변화
@router.get("/users/{user_id}/metric_changes", response_model=MetricChangeCardResponse)
async def get_user_metric_changes(
    user_id:int,
    db:AsyncSession=Depends(get_db)
):
    from app.service.metric_tracker import get_metric_changes
    try:
        return await get_metric_changes(db, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"지표 변화 분석 중 오류: {e}")


# 인터뷰 진행 상태 조회
@router.get("/{i_id}/status")
async def get_interview_status(i_id:int, db:AsyncSession=Depends(get_db)):
    interview=await crud.get_i(db, i_id)
    if not interview:
        raise HTTPException(status_code=404, detail="인터뷰를 찾을 수 없습니다.")

    return {
        "i_id":i_id,
        "status":interview.status,
        "current_question":interview.current_question,
        "total_questions":interview.total_questions,
        "language":interview.language,
    }
