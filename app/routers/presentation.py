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
        print(f"\n=== 분석 오류 발생 ===")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        print(f"====================\n")
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
        "success": True, # 응답 결과
        "data": {
            "pr_id": presentation.pr_id,
            "title": presentation.title, # 발표 제목
            "description": presentation.description, # 발표 설명
            "results": [ # 결과
                {
                    "result_id": r.result_id,
                    "duration_min": r.duration_min,
                    "emotion": "Anxious" if r.anxiety_ratio > r.embarrassment_ratio else "Embarrassed" # 일단 '불안/당황' 만 응답 향 후 변경 가능성 있음
                }
                for r in presentation.results
            ],
            "feedbacks": [
                {
                    "feedback_id": f.feedback_id,
                    "brief": f.brief_feedback, # 간단한 피드백
                    "scores": { # 점수
                        "volume": f.volume_score, # 목소리 점수
                        "pitch": f.pitch_score, # 피치 점수
                        "speed": f.speed_score, # 말하기 속도 점수
                        "silence": f.silence_score, # 침묵 구간 점수
                        "clarity": f.clarity_score, # 명료함(또박또박, 정확하게) 점수
                        "overall": f.overall_score # 종합 점수
                    }
                }
                for f in presentation.feedbacks
            ]
        }
    }