from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.database import get_db
from ..database.crud.presentation import PresentationCRUD
from ..service.presentation_analysis_service import get_presentation_analysis_service
from typing import Optional
import tempfile
import os

router = APIRouter(prefix="/presentations", tags=["Presentation"])


# 새 발표 생성
@router.post("/create")
async def create_presentation(user_id: int = Form(...), title: str = Form(...), description: Optional[str] = Form(None), target_duration: Optional[int] = Form(None), db: AsyncSession = Depends(get_db)):
    presentation = await PresentationCRUD.create_presentation(db=db, user_id=user_id, title=title, description=description, target_duration=target_duration)

    return {"success": True, "pr_id": presentation.pr_id}


# 발표 음성 파일 업로드 및 분석
@router.post("/{pr_id}/analyze")
async def analyze_presentation(pr_id: int, audio_file: UploadFile = File(...), estimated_syllables: Optional[int] = Form(None), db: AsyncSession = Depends(get_db)):

    # 파일 저장
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            contents = await audio_file.read()
            tmp.write(contents)
            temp_file = tmp.name

        file_size = len(contents)

        # 음성 파일 DB 등록
        voice_file = await PresentationCRUD.create_voice_file(db=db, pr_id=pr_id, file_path=temp_file, original_filename=audio_file.filename, file_size=file_size)

        # 분석 + 피드백 생성 + 저장
        service = get_presentation_analysis_service()
        result = await service.analyze_and_save(db=db, pr_id=pr_id, v_f_id=voice_file.v_f_id, audio_path=temp_file, estimated_syllables=estimated_syllables)

        return result

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)


# 발표 상세 조회 (분석 결과 + 피드백 포함)
@router.get("/{pr_id}")
async def get_presentation(pr_id: int, db: AsyncSession = Depends(get_db)):
    presentation = await PresentationCRUD.get_presentation_with_details(db, pr_id)

    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return {
        "success": True,
        "data": {
            "pr_id": presentation.pr_id,
            "title": presentation.title,
            "description": presentation.description,
            "results": [
                {
                    "result_id": r.result_id,
                    "duration_min": float(r.duration_min) if r.duration_min else 0.0,
                    "avg_volume_db": float(r.avg_volume_db) if r.avg_volume_db else 0.0,
                    "avg_pitch": float(r.avg_pitch) if r.avg_pitch else 0.0,
                    "silence_ratio": float(r.silence_ratio) if r.silence_ratio else 0.0,
                    "speech_rate": float(r.speech_rate_actual or r.speech_rate_total or 0),
                    "emotion": "Anxious" if (r.anxiety_ratio or 0) > (r.embarrassment_ratio or 0) else "Embarrassed",
                    "emotion_confidence": float(max(r.anxiety_ratio or 0, r.embarrassment_ratio or 0))
                }
                for r in presentation.results
            ],
            "feedbacks": [
                {
                    "feedback_id": f.feedback_id,
                    "brief": f.brief_feedback or "",
                    "detailed_summary": f.detailed_summary or "",
                    "detailed_strengths": f.detailed_strengths or "",
                    "detailed_improvements": f.detailed_improvements or "",
                    "detailed_advice": f.detailed_advice or "",
                    "scores": {
                        "volume": int(f.volume_score) if f.volume_score else 0,
                        "pitch": int(f.pitch_score) if f.pitch_score else 0,
                        "speed": int(f.speed_score) if f.speed_score else 0,
                        "silence": int(f.silence_score) if f.silence_score else 0,
                        "clarity": int(f.clarity_score) if f.clarity_score else 0,
                        "overall": int(f.overall_score) if f.overall_score else 0
                    }
                }
                for f in presentation.feedbacks
            ]
        }
    }