from app.service.analysis_service import get_analysis_service
from pathlib import Path
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.service.chroma_service import i_process_answer
from app.database.database import get_db
from app.database.models.interview import InterviewAnswer
from app.database.schemas.interview import AnalyzeRequest,InterviewReport,ProcessAnswerResponse,AnswerUploadResponse
from app.database.crud.interview import get_answer, save_answer_audio


router=APIRouter(prefix="/interview", tags=["interview"])


@router.post("/analyze", response_model=InterviewReport)
async def analyze_interview(request:AnalyzeRequest):
    try:
        service=get_analysis_service()
        result=await service.analyze_interview(request.transcript)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")  



@router.post("/answers/{answer_id}/process", response_model=ProcessAnswerResponse)
async def process_interview_answer(
    answer_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await i_process_answer(answer_id, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"처리 중 오류: {e}")


@router.post("/answers/{answer_id}/upload", response_model=AnswerUploadResponse)
async def upload_interview_answer_audio(
    answer_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    answer = await get_answer(db, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="answer_id를 찾을 수 없습니다.")

    data = await file.read()
    await save_answer_audio(db, answer, data, file.filename)

    return AnswerUploadResponse(
        answer_id=answer_id,
        audio_format=answer.audio_format or "",
        size=len(data),
    )
