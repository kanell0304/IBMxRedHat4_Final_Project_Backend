from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.communication import Communication, CVoiceFile, CSTTResult
from typing import Optional

# 대화분석 CRUD

async def create_communication(db: AsyncSession, user_id: int) -> Communication:
    communication = Communication(user_id=user_id)
    db.add(communication)
    await db.commit()
    await db.refresh(communication)
    return communication


async def get_communication_by_id(db: AsyncSession, c_id: int) -> Optional[Communication]:
    result = await db.execute(
        select(Communication).where(Communication.c_id == c_id)
    )
    return result.scalar_one_or_none()


async def create_voice_file(
    db: AsyncSession,
    c_id: int,
    filename: str,
    original_format: str,
    data: bytes,
    duration: Optional[float]
) -> CVoiceFile:
    voice_file = CVoiceFile(
        c_id=c_id,
        filename=filename,
        original_format=original_format,
        data=data,
        duration=duration
    )
    db.add(voice_file)
    await db.commit()
    await db.refresh(voice_file)
    return voice_file


async def create_stt_result(
    db: AsyncSession,
    c_id: int,
    c_vf_id: int,
    json_data: dict
) -> CSTTResult:
    stt_result = CSTTResult(
        c_id=c_id,
        c_vf_id=c_vf_id,
        json_data=json_data
    )
    db.add(stt_result)
    await db.commit()
    await db.refresh(stt_result)
    return stt_result


async def get_voice_file_by_c_id(db: AsyncSession, c_id: int) -> Optional[CVoiceFile]:
    result = await db.execute(
        select(CVoiceFile).where(CVoiceFile.c_id == c_id)
    )
    return result.scalar_one_or_none()