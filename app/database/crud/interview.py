from pathlib import Path
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from app.database.models.interview import Interview, InterviewAnswer, InterviewResult, InterviewType


async def create_i(db, user_id:int, interview_type:InterviewType, category_id:Optional[int], total_questions:int):
  interview = Interview(
    user_id=user_id,
    interview_type=interview_type,
    category_id=category_id,
    total_questions=total_questions,
    status=0,
  )
  db.add(interview)
  await db.commit()
  await db.refresh(interview)
  return interview


async def get_i(db, i_id: int):
  result = await db.execute(select(Interview).where(Interview.i_id == i_id).options(selectinload(Interview.answers)))
  return result.scalar_one_or_none()


async def list_i(db, user_id: int):
  result = await db.execute(
    select(Interview).where(Interview.user_id == user_id).order_by(Interview.created_at.desc())
  )
  return result.scalars().all()


async def create_answer(
  db, i_id: int, q_id: Optional[int], q_order: Optional[int],
  duration_sec: Optional[int], transcript: Optional[str], labels_json: Optional[dict]):

  answer = InterviewAnswer(
    i_id=i_id,
    q_id=q_id,
    q_order=q_order,
    duration_sec=duration_sec,
    transcript=transcript,
    labels_json=labels_json,
  )
  db.add(answer)
  await db.commit()
  await db.refresh(answer)
  return answer


async def get_answer(db, answer_id: int):
  result = await db.execute(select(InterviewAnswer).where(InterviewAnswer.i_answer_id == answer_id))
  return result.scalar_one_or_none()


async def delete_answer(answer_id: int, i_id: int, db):
  result = await db.execute(delete(InterviewAnswer).where(InterviewAnswer.i_answer_id == answer_id,InterviewAnswer.i_id == i_id))
  await db.commit()
  return result.rowcount > 0


async def complete_i(db, i_id: int):
  result = await db.execute(select(Interview).where(Interview.i_id == i_id))
  interview = result.scalar_one_or_none()
  if not interview:
    return None
  
  interview.status = 2
  await db.commit()
  await db.refresh(interview)
  return interview


async def list_results(db, i_id: int):
  result = await db.execute(select(InterviewResult).where(InterviewResult.i_id == i_id))
  return result.scalars().all()


async def delete_i(db, i_id: int):
  result = await db.execute(delete(Interview).where(Interview.i_id == i_id))
  await db.commit()
  return result.rowcount > 0


async def save_audio(db, answer: InterviewAnswer, data: bytes, filename: str, duration_sec: Optional[int] = None):
  ext = (Path(filename).suffix or ".wav").lstrip(".")
  answer.audio_data = data
  answer.audio_format = ext
  answer.audio_path = None
  if duration_sec is not None:
    answer.duration_sec = duration_sec
  await db.commit()
  await db.refresh(answer)
  return answer