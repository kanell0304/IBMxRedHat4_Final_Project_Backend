from fastapi import APIRouter, HTTPException
from app.service.analysis_service import get_analysis_service
from app.database.schemas.interview import AnalyzeRequest, InterviewReport


router=APIRouter(prefix="/interview", tags=["interview"])


@router.post("/analyze", response_model=InterviewReport)
async def analyze_interview(request:AnalyzeRequest):
    try:
        service=get_analysis_service()
        result=await service.analyze_interview(request.transcript)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"{e}")  