from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.interview import InterviewAnswer


async def get_answer(answer_id: int, db: AsyncSession):
  result = await db.execute(
    select(InterviewAnswer).where(InterviewAnswer.i_answer_id == answer_id)
  )
  return result.scalar_one_or_none()

async def save_answer_audio(answer: InterviewAnswer, data: bytes, filename: str, db: AsyncSession):
  ext = (Path(filename).suffix or ".wav").lstrip(".")
  answer.audio_data = data
  answer.audio_format = ext
  answer.audio_path = None
  await db.commit()
  await db.refresh(answer)
  return answer