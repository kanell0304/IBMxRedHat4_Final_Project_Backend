from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.crud import communication as crud
from app.database.schemas.communication import CommunicationResponse, VoiceFileResponse, STTResultResponse
from app.service.audio_service import AudioService
from app.service.stt_service import STTService
from app.core.settings import settings

router = APIRouter(prefix="/communication", tags=["Communication"])

audio_service = AudioService()
stt_service = STTService(project_id=settings.google_cloud_project_id)


@router.post("/upload", response_model=CommunicationResponse)
async def upload_wav(
    user_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    communication = await crud.create_communication(db, user_id)
    
    audio_data = await file.read()
    original_format = file.filename.split('.')[-1]
    
    wav_data, duration = audio_service.convert_to_wav(audio_data, original_format)
    
    await crud.create_voice_file(
        db=db,
        c_id=communication.c_id,
        filename=file.filename,
        original_format=original_format,
        data=audio_data,
        duration=duration
    )
    
    return communication


@router.post("/{c_id}/stt", response_model=STTResultResponse)
async def process_stt(
    c_id: int,
    db: AsyncSession = Depends(get_db)
):
    communication = await crud.get_communication_by_id(db, c_id)
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    voice_file = await crud.get_voice_file_by_c_id(db, c_id)
    if not voice_file:
        raise HTTPException(status_code=404, detail="Voice file not found")

    wav_data, _ = audio_service.convert_to_wav(voice_file.data, voice_file.original_format)

    chirp_result = await stt_service.transcribe_chirp(wav_data)

    stt = await crud.create_stt_result(
        db=db,
        c_id=c_id,
        c_vf_id=voice_file.c_vf_id,
        json_data=chirp_result
    )

    return stt


@router.get("/health")
async def stt_health_check():
    """STT 서비스 상태 확인"""
    try:
        project_id = settings.google_cloud_project_id
        return {
            "status": "ok",
            "service": "Google Speech-to-Text",
            "project_id": project_id,
            "model": "chirp_3"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }