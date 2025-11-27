"""
음성 분석 API 라우터
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import tempfile
import os
from app.service.voice_analyzer import get_analyzer

router = APIRouter(
    prefix="/voice",
    tags=["voice-analysis"]
)


@router.post("/analyze")
async def analyze_voice(
        audio_file: UploadFile = File(..., description="음성 파일 (.wav)"),
        estimated_syllables: Optional[int] = Form(None, description="추정 음절 수 (선택사항)")
):
    """
    음성 파일 분석 API

    **기능:**
    - Anxious/Embarrassed 감정 분석
    - 음향 특징 분석 (음량, 피치, 발화 속도 등)

    **Parameters:**
    - audio_file: .wav 형식의 음성 파일
    - estimated_syllables: 발표 내용의 음절 수 (선택, 발화 속도 계산에 사용)

    **Returns:**
```json
    {
        "success": true,
        "data": {
            "emotion": "Anxious",
            "emotion_confidence": 73.57,
            "emotion_scores": {
                "Anxious": 73.57,
                "Embarrassed": 26.43
            },
            "duration": 60.0,
            "duration_min": 1.0,
            "avg_volume_db": -18.7,
            "avg_pitch": 227.14,
            "speech_rate_actual": 37.98,
            ...
        }
    }
```
    """
    # 파일 형식 확인
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(
            status_code=400,
            detail="Only .wav files are supported"
        )

    # 임시 파일로 저장
    temp_file = None
    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            contents = await audio_file.read()
            tmp.write(contents)
            temp_file = tmp.name

        # 분석기 가져오기
        analyzer = get_analyzer()

        # 분석 실행
        result = analyzer.analyze(
            audio_path=temp_file,
            estimated_syllables=estimated_syllables
        )

        # 에러 체크
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {result['error']}"
            )

        return JSONResponse(content={
            "success": True,
            "data": result
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

    finally:
        # 임시 파일 삭제
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass


@router.get("/health")
async def health_check():
    """
    헬스 체크 API

    **Returns:**
```json
    {
        "status": "ok",
        "analyzer": "loaded"
    }
```
    """
    try:
        analyzer = get_analyzer()
        return {
            "status": "ok",
            "analyzer": "loaded",
            "device": str(analyzer.device),
            "emotions": list(analyzer.idx_to_emotion.values())
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }