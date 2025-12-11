import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from pydub import AudioSegment
from app.service.chroma_service import i_process_answer
from app.database.database import get_db
from app.service.analysis_service import get_analysis_service
from app.service.i_start_service import start_interview_session
from app.database.schemas.interview import AnalyzeReq, I_Report, ProcessAnswerResponse, AnswerUploadResponse, I_Create, I_Basic, I_Detail, AnswerCreate, Answer, I_Result, I_StartReq, I_StartRes
from app.database.crud import interview as interview_crud
from app.service.i_stats_service import compute_interview_stt_metrics
from app.service.llm_service import OpenAIService
from app.service.chroma_service import i_process_answer, analyze_weakness_patterns, analyze_speech_style_evolution


router=APIRouter(prefix="/interview", tags=["interview"])


# DB 질문 기반 인터뷰 시작
@router.post("/start", response_model=I_StartRes)
async def start_interview(payload: I_StartReq, db = Depends(get_db)):
    try:
        return await start_interview_session(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"면접 생성 중 오류: {e}")


# 대화 전체 분석
@router.post("/analyze", response_model=I_Report)
async def analyze(request:AnalyzeReq, db=Depends(get_db)):
    try:
        interview=await interview_crud.get_i(db, request.i_id)
        if not interview:
            raise HTTPException(status_code=404, detail="해당 모의면접을 찾을 수 없습니다.")
        
        service=get_analysis_service()
        report=await service.analyze_interview(request.transcript)

        await interview_crud.create_result(
            db=db,
            user_id=interview.user_id,
            i_id=request.i_id,
            scope="overall",
            report_json=report.model_dump()
        )

        return report
    
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")

# 인터뷰 전체 종합 분석
@router.post("/{i_id}/analyze_full", response_model=I_Report)
async def analyze_interview_full(i_id:int, db=Depends(get_db)):
    try:
        interview=await interview_crud.get_i(db, i_id)
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

            question=await interview_crud.get_question(db, answer.q_id) if answer.q_id else None
            qa_list.append({
                "question":question.question_text if question else "",
                "answer":answer.transcript
            })
        
        if not transcripts:
            raise HTTPException(status_code=400, detail="처리된 답변이 없습니다.")
        full_transcript=" ".join(transcripts)

        from app.service.i_bert_service import get_inference_service
        bert_service=get_inference_service()
        bert_analysis=bert_service.predict_labels(full_transcript)

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

        await interview_crud.create_result(
            db=db,
            user_id=interview.user_id,
            i_id=i_id,
            scope="overall",
            report_json=report.model_dump()
        )

        await interview_crud.update_interview(db, i_id, status=2)

        return report
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 : {e}")


# 개별 답변 라벨링/문장 분해 처리
@router.post("/answers/{answer_id}/process", response_model=ProcessAnswerResponse)
async def process_answer(answer_id: int, db = Depends(get_db)):
    try:
        return await i_process_answer(answer_id, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류: {e}")


# 답변 오디오 업로드
@router.post("/answers/{answer_id}/upload", response_model=AnswerUploadResponse)
async def upload_answer_audio(answer_id: int, file: UploadFile = File(...), db = Depends(get_db)):
    answer = await interview_crud.get_answer(db, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="answer_id를 찾을 수 없습니다.")

    data = await file.read()
    ext = (file.filename.split(".")[-1] if "." in file.filename else "wav") or "wav"
    duration_sec = None
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}") as tmp:
            tmp.write(data)
            tmp.flush()
            audio = AudioSegment.from_file(tmp.name)
            duration_sec = int(round(len(audio) / 1000))
    except Exception:
        duration_sec = None  # 길이 계산 실패 시 넘어감

    await interview_crud.save_audio(db, answer, data, file.filename, duration_sec)

    return AnswerUploadResponse(
        answer_id=answer_id,
        audio_format=answer.audio_format or "",
        size=len(data),
    )


# 인터뷰 생성
@router.post("", response_model=I_Basic)
async def create_i(payload: I_Create, db = Depends(get_db)):
    return await interview_crud.create_i(
        db=db,
        user_id=payload.user_id,
        interview_type=payload.interview_type,
        category_id=payload.category_id,
        total_questions=payload.total_questions,
    )


# 인터뷰 단건 조회
@router.get("/{i_id}", response_model=I_Detail)
async def get_i(i_id: int, db = Depends(get_db)):
    i = await interview_crud.get_i(db, i_id)
    if not i:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return i


# 사용자별 인터뷰 목록
@router.get("/users/{user_id}/interviews", response_model=list[I_Basic])
async def list_user_i(user_id: int, db = Depends(get_db)):
    return await interview_crud.list_i(db, user_id)


# 답변 생성/저장
@router.post("/{i_id}/answers", response_model=Answer)
async def create_answer_i(i_id: int, payload: AnswerCreate, db = Depends(get_db)):
    i = await interview_crud.get_i(db, i_id)
    if not i:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")

    return await interview_crud.create_answer(
        db=db,
        i_id=i_id,
        q_id=payload.q_id,
        q_order=payload.q_order,
        duration_sec=payload.duration_sec,
        transcript=payload.transcript,
        labels_json=payload.labels_json,
    )


# 답변 삭제
@router.delete("/{i_id}/answers/{answer_id}", status_code=204)
async def delete_answer_i(i_id: int, answer_id: int, db = Depends(get_db)):
    deleted = await interview_crud.delete_answer(answer_id, i_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)


# 인터뷰 완료 처리
@router.post("/{i_id}/complete", response_model=I_Basic)
async def complete_i(i_id: int, db = Depends(get_db)):
    i = await interview_crud.complete_i(db, i_id)
    if not i:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return i


# 인터뷰 결과 조회
@router.get("/{i_id}/results", response_model=list[I_Result])
async def get_results(i_id: int, db = Depends(get_db)):
    return await interview_crud.list_results(db, i_id)


# 인터뷰 삭제
@router.delete("/{i_id}", status_code=204)
async def delete_i(i_id: int, db = Depends(get_db)):
    deleted = await interview_crud.delete_i(db, i_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="데이터가 없습니다")
    return Response(status_code=204)
