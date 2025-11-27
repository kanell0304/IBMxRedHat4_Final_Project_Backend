from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import tempfile
import os
from app.service.voice_analyzer import get_analyzer

router = APIRouter(prefix="/voice", tags=["voice-analysis"])


@router.post("/analyze")
async def analyze_voice(audio_file: UploadFile = File(..., description="음성 파일 (.wav)"), estimated_syllables: Optional[int] = Form(None, description="추정 음절 수 (선택사항)")):

    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only .wav files are supported")

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
        result = analyzer.analyze(audio_path=temp_file, estimated_syllables=estimated_syllables)

        # 에러 체크
        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {result['error']}")

        return JSONResponse(content={"success": True, "data": result})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        # 임시 파일 삭제
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except:
                pass

# 서버 구동 상태 확인
@router.get("/health")
async def health_check():
    try:
        analyzer = get_analyzer()
        return {
            "status": "ok",
            "analyzer": "loaded",
            "device": str(analyzer.device),
            "emotions": list(analyzer.idx_to_emotion.values())
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}