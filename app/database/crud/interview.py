from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from app.database.models.interview import Interview, InterviewAnswer, InterviewResult, InterviewType, InterviewQuestion, QuestionType, DifficultyLevel

# mock interview
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


async def update_interview(db, i_id: int, current_question: Optional[int] = None, status: Optional[int] = None):
  interview=await get_i(db, i_id)
  if not interview:
    return None
  if current_question is not None:
    interview.current_question=current_question
  if status is not None:
    interview.status=status

  await db.commit()
  await db.refresh(interview)
  return interview


async def list_i(db, user_id: int):
  result = await db.execute(
    select(Interview).where(Interview.user_id == user_id).order_by(Interview.created_at.desc())
  )
  return result.scalars().all()


async def complete_i(db, i_id: int):
  result = await db.execute(select(Interview).where(Interview.i_id == i_id))
  interview = result.scalar_one_or_none()
  if not interview:
    return None
  
  interview.status = 2
  await db.commit()
  await db.refresh(interview)
  return interview


async def delete_i(db, i_id: int):
  try:
    await db.execute(delete(InterviewResult).where(InterviewResult.i_id == i_id))
    await db.execute(delete(InterviewAnswer).where(InterviewAnswer.i_id == i_id))
    result = await db.execute(delete(Interview).where(Interview.i_id == i_id))
    await db.commit()
    return result.rowcount > 0
  except Exception:
    await db.rollback()
    raise


# mock interview question
async def get_question(db, q_id: int):
  result=await db.execute(
    select(InterviewQuestion).where(InterviewQuestion.q_id==q_id)
  )

  return result.scalar_one_or_none()

async def list_question(db, q_type: Optional[QuestionType] = None, category_id: Optional[int] = None, difficulty: Optional[DifficultyLevel]= None, language: Optional[str] = None):
  query=select(InterviewQuestion)

  if q_type is not None:
    query=query.where(InterviewQuestion.question_type==q_type)
  if category_id is not None:
    query=query.where(InterviewQuestion.category_id==category_id)
  if difficulty is not None:
    query=query.where(InterviewQuestion.difficulty==difficulty)
  if language is not None:
    query=query.where(InterviewQuestion.language==language)

  result=await db.execute(query.order_by(InterviewQuestion.q_id))
  return result.scalars().all()



# mock interview answer
async def create_answer(
  db, i_id: int, q_id: int, q_order: int):
  answer = InterviewAnswer(
    i_id=i_id,
    q_id=q_id,
    q_order=q_order,
  )
  db.add(answer)
  await db.commit()
  await db.refresh(answer)
  return answer


async def get_answer(db, answer_id: int):
  result = await db.execute(select(InterviewAnswer).where(InterviewAnswer.i_answer_id == answer_id))
  return result.scalar_one_or_none()

async def update_answer(db, answer_id: int, transcript: Optional[str] = None, labels_json: Optional[dict] = None, stt_metrics_json: Optional[dict] = None):
  answer = await get_answer(db, answer_id)
  if not answer:
    return None
  
  if transcript is not None:
    answer.transcript=transcript
  if labels_json is not None:
    answer.labels_json=labels_json
  if stt_metrics_json is not None:
    answer.stt_metrics_json=stt_metrics_json

  await db.commit()
  await db.refresh(answer)
  return answer

async def delete_answer(answer_id: int, i_id: int, db):
  result = await db.execute(delete(InterviewAnswer).where(InterviewAnswer.i_answer_id == answer_id,InterviewAnswer.i_id == i_id))
  await db.commit()
  return result.rowcount > 0


# mock interview result
async def create_result(db, user_id: int, i_id: int, scope: str, report: dict, i_answer_id: Optional[int] = None, q_id: Optional[int] = None):
  result=InterviewResult(
    user_id=user_id,
    i_id=i_id,
    scope=scope,
    report=report,
    i_answer_id=i_answer_id,
    q_id=q_id
  )

  db.add(result)
  await db.commit()
  await db.refresh(result)
  return result

async def get_result(db, result_id: int):
  result=await db.execute(
    select(InterviewResult).where(InterviewResult.i_result_id==result_id)
  )
  return result.scalar_one_or_none()


async def list_results(db, i_id: int):
  result = await db.execute(select(InterviewResult).where(InterviewResult.i_id == i_id))
  return result.scalars().all()


# scope=overall 조회
async def get_result_by_scope(db, i_id:int, scope:str):
  result=await db.execute(
    select(InterviewResult).where(
      InterviewResult.i_id==i_id,
      InterviewResult.scope==scope
    ).limit(1)
  )
  return result.scalar_one_or_none()

# scope=per_question 전체 조회
async def get_results_by_scope(db, i_id:int, scope:str):
  result=await db.execute(
    select(InterviewResult).where(
      InterviewResult.i_id==i_id,
      InterviewResult.scope==scope
    ).order_by(InterviewResult.i_result_id)
  )
  return result.scalars().all()