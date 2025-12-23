from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.service.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/convert-to-wav")
async def convert_audio_to_wav(
    audio_file: UploadFile = File(...)
):
    try:
        filename = audio_file.filename or ""
        file_extension = filename.split(".")[-1].lower() if "." in filename else "wav"

        supported_formats = ["mp3", "m4a", "wav", "webm", "ogg", "flac", "aac"]
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 포맷입니다. 지원 포맷: {', '.join(supported_formats)}"
            )

        audio_data = await audio_file.read()

        if not audio_data:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        wav_data, duration = AudioService.convert_to_wav(audio_data, file_extension)

        return Response(
            content=wav_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="converted.wav"',
                "X-Audio-Duration": str(duration)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"오디오 변환 중 오류가 발생했습니다: {str(e)}"
        )


@router.post("/get-audio-info")
async def get_audio_info(
    audio_file: UploadFile = File(...)
):
    try:
        filename = audio_file.filename or ""
        file_extension = filename.split(".")[-1].lower() if "." in filename else "wav"

        audio_data = await audio_file.read()

        if not audio_data:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")

        wav_data, duration = AudioService.convert_to_wav(audio_data, file_extension)

        return {
            "success": True,
            "data": {
                "filename": filename,
                "original_format": file_extension,
                "original_size_bytes": len(audio_data),
                "wav_size_bytes": len(wav_data),
                "duration_seconds": duration,
                "sample_rate": 16000,
                "channels": 1,
                "bit_depth": 16
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"오디오 정보 추출 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "audio_conversion",
        "supported_formats": ["mp3", "m4a", "wav", "webm", "ogg", "flac", "aac"]
    }
