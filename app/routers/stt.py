from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.service.stt_service import STTService
from app.core.settings import settings

router = APIRouter(prefix="/stt", tags=["speech-to-text"])


@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="음성 파일 (.wav)"),
    project_id: str = Form(None, description="Google Cloud Project ID (선택사항)")
):
    """
    WAV 파일을 업로드하여 STT 변환 수행
    - Chirp 모델: 화자 분리
    - Long 모델: 상세 텍스트 + 타임스탬프
    """

    # 파일 확장자 검증
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only .wav files are supported")

    try:
        # Project ID 설정 (Form으로 받거나 환경변수 사용)
        project_id = project_id or settings.google_cloud_project_id

        if not project_id:
            raise HTTPException(
                status_code=400,
                detail="Project ID is required. Provide it in the form or set GOOGLE_CLOUD_PROJECT_ID in .env"
            )

        # WAV 파일 읽기
        wav_data = await audio_file.read()

        # STT 서비스 초기화
        stt_service = STTService(project_id=project_id)

        # 두 모델로 변환 수행
        chirp_result = await stt_service.transcribe_chirp(wav_data)
        long_result = await stt_service.transcribe_long(wav_data)

        return JSONResponse(content={
            "success": True,
            "project_id": project_id,
            "chirp_transcription": chirp_result,
            "long_transcription": long_result
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"STT processing failed: {str(e)}"
        )


@router.get("/health")
async def stt_health_check():
    """STT 서비스 상태 확인"""
    try:
        project_id = settings.google_cloud_project_id
        return {
            "status": "ok",
            "service": "Google Speech-to-Text",
            "project_id": project_id,
            "models": ["chirp", "long"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    