from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.service.analysis_service import get_analysis_service
from app.service.chroma_service import i_process_answer
from app.database.database import get_db
from app.database.models.interview import InterviewAnswer
from app.database.schemas.interview import (
    AnalyzeRequest,
    InterviewReport,
    ProcessAnswerResponse,
    AnswerUploadResponse,
)


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
    """
    - answer_id로 인터뷰 답변을 조회
    - transcript가 없으면 audio_path를 STT로 변환 후 저장
    - BERT 분류 결과를 저장
    - chromadb에 transcript+메타데이터 저장
    """
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
    """
    STT/Chroma 테스트용: 특정 answer_id의 audio_path를 업로드한 파일로 교체
    """
    answer = await db.get(InterviewAnswer, answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="answer_id를 찾을 수 없습니다.")

    data = await file.read()
    ext = Path(file.filename).suffix or ".wav"

    base_dir = Path(__file__).resolve().parents[2] / "data" / "answers"
    base_dir.mkdir(parents=True, exist_ok=True)
    save_path = base_dir / f"answer_{answer_id}{ext}"

    save_path.write_bytes(data)

    answer.audio_path = str(save_path)
    await db.commit()
    await db.refresh(answer)

    return AnswerUploadResponse(
        answer_id=answer_id,
        audio_path=answer.audio_path,
    )
