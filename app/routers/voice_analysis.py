from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import tempfile
import os

# ffmpeg 경로 설정 -> 현재 c:/ffmpeg 폴더 안에 있음
os.environ["PATH"] = r"C:\ffmpeg\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment

from ..service.audio_service import AudioService
from ..service.voice_analyzer import get_analyzer

router = APIRouter(prefix="/voice", tags=["voice-analysis"])

# 발표 녹음 파일 분석
@router.post("/analyze")
async def analyze_voice(audio_file: UploadFile = File(..., description="음성 파일 (.wav, .mp3, .m4a, .ogg 등)"), estimated_syllables: Optional[int] = Form(None, description="추정 음절 수 (선택사항)")):
    supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac', '.wma']

    file_extension = os.path.splitext(audio_file.filename)[1].lower()
    if file_extension not in supported_formats:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Supported formats: {', '.join(supported_formats)}")

    temp_wav_file = None

    try:
        # 업로드된 파일을 메모리에서 읽기
        audio_data = await audio_file.read()

        # AudioService로 메모리에서 wav로 변환 (빠름!)
        wav_data, duration = AudioService.convert_to_wav(audio_data, file_extension)

        # 분석을 위해 변환된 wav만 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(wav_data)
            temp_wav_file = tmp.name

        # 음성 분석 실행
        analyzer = get_analyzer()
        result = analyzer.analyze(audio_path=temp_wav_file, estimated_syllables=estimated_syllables)

        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {result['error']}")

        # duration도 활용 가능
        result['duration'] = duration  # 추가 정보

        return JSONResponse(content={"success": True, "data": result})

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        if temp_wav_file and os.path.exists(temp_wav_file):
            try:
                os.unlink(temp_wav_file)
            except Exception:
                pass

# 서버 상태 확인
@router.get("/health")
async def health_check():
    try:
        analyzer = get_analyzer() # 분석 기능 불러오기
        return {
            "status": "ok", # 상태
            "analyzer": "loaded", # 분석 모델 로딩 상태
            "device": str(analyzer.device), # 작동 장치 종류
            "emotions": list(analyzer.idx_to_emotion.values()) # 어떤 감정들을 분석 가능한지
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
