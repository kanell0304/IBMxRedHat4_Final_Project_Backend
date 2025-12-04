from app.service.analysis_service import get_analysis_service
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.service.chroma_service import i_process_answer
from app.database.database import get_db
from app.database.models.interview import InterviewAnswer
from app.database.schemas.interview import AnalyzeRequest, InterviewReport, ProcessAnswerResponse, AnswerUploadResponse


router=APIRouter(prefix="/interview", tags=["interview"])


@router.post("/analyze", response_model=InterviewReport)
async def analyze_interview(request:AnalyzeRequest):
    try:
        service=get_analysis_service()
        result=await service.analyze_interview(request.transcript)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")  