import random
from typing import List, Optional
from sqlalchemy import select
from app.database.crud.category import get_jobcategory
from app.database.models.category import JobCategory
from app.database.models.interview import Interview, InterviewAnswer, InterviewQuestion, InterviewType, QuestionType, DifficultyLevel
from app.database.schemas.interview import I_StartReq, I_StartRes, I_StartQ


QUESTION_TYPE_ALIAS = {
    "공통질문만": "common",
    "직무관련": "job",
    "섞어서": "mixed",
}


def norm_q_type(question_type: str) -> str:
    key = (question_type or "").strip()
    if key in QUESTION_TYPE_ALIAS:
        return QUESTION_TYPE_ALIAS[key]

    lowered = key.lower()
    if lowered in ("common", "job", "mixed"):
        return lowered

    raise ValueError("question_type은 common | job | mixed 중 하나여야 합니다.")


def norm_diff(difficulty: Optional[str]) -> Optional[DifficultyLevel]:
    if not difficulty:
        return None
    return {
        "easy": DifficultyLevel.EASY,
        "mid": DifficultyLevel.MID,
        "hard": DifficultyLevel.HARD,
        "쉬움": DifficultyLevel.EASY,
        "중간": DifficultyLevel.MID,
        "어려움": DifficultyLevel.HARD,
    }.get(difficulty.strip().lower())


async def get_jobcat(db, job_role: Optional[str]) -> JobCategory:
    if not job_role:
        raise ValueError("직무(role)를 선택하세요.")

    category = await get_jobcategory(db, job_category_name=job_role)
    if not category:
        raise ValueError("요청한 직무 카테고리를 찾을 수 없습니다.")
    return category


async def load_q(
    db, *, question_type: str, category_id: Optional[int], total_questions: int, difficulty: Optional[DifficultyLevel]
) -> List[InterviewQuestion]:
    def _apply_difficulty(query):
        if difficulty:
            return query.where(InterviewQuestion.difficulty == difficulty)
        return query

    if question_type == "common":
        query = select(InterviewQuestion).where(InterviewQuestion.question_type == QuestionType.COMMON)
        result = await db.execute(_apply_difficulty(query))
        commons = result.scalars().all()
        if len(commons) < total_questions:
            raise ValueError("공통 질문 수가 충분하지 않습니다.")
        return random.sample(commons, total_questions)

    if question_type == "job":
        if not category_id:
            raise ValueError("직무 질문에는 job_role이 필요합니다.")
        query = select(InterviewQuestion).where(
            InterviewQuestion.question_type == QuestionType.JOB,
            InterviewQuestion.category_id == category_id,
        )
        result = await db.execute(_apply_difficulty(query))
        jobs = result.scalars().all()
        if len(jobs) < total_questions:
            raise ValueError("해당 직무 질문 수가 충분하지 않습니다.")
        return random.sample(jobs, total_questions)

    # mixed
    if not category_id:
        raise ValueError("섞어서 선택 시 직무 정보를 함께 전달해주세요.")

    common_query = select(InterviewQuestion).where(InterviewQuestion.question_type == QuestionType.COMMON)
    job_query = select(InterviewQuestion).where(
        InterviewQuestion.question_type == QuestionType.JOB,
        InterviewQuestion.category_id == category_id,
    )

    common_result = await db.execute(_apply_difficulty(common_query))
    job_result = await db.execute(_apply_difficulty(job_query))
    commons = common_result.scalars().all()
    jobs = job_result.scalars().all()
    pool = commons + jobs

    if len(pool) < total_questions:
        raise ValueError("공통/직무 질문 수가 충분하지 않습니다.")

    # 직무 비중 우선: 기본적으로 (총문항-2)개는 직무, 나머지 공통을 목표
    target_job = min(len(jobs), max(1, total_questions - 2))
    target_common = total_questions - target_job

    selected_jobs = random.sample(jobs, target_job) if target_job > 0 else []
    selected_commons = random.sample(commons, target_common) if target_common > 0 else []
    selected = selected_jobs + selected_commons

    # 한쪽이 부족한 경우 풀에서 남은 질문으로 채움
    if len(selected) < total_questions:
        remaining_pool = [q for q in pool if q not in selected]
        selected.extend(random.sample(remaining_pool, total_questions - len(selected)))

    return selected


async def start_interview_session(
    db, payload: I_StartReq
) -> I_StartRes:
    q_type = norm_q_type(payload.question_type)
    total_questions = payload.total_questions or 5

    category: Optional[JobCategory] = None
    if q_type in ("job", "mixed"):
        category = await get_jobcat(db, payload.job_role)

    # 공통질문만 선택 시 난이도는 무시
    difficulty = None if q_type == "common" else norm_diff(payload.difficulty)

    questions = await load_q(
        db,
        question_type=q_type,
        category_id=category.job_category_id if category else None,
        total_questions=total_questions,
        difficulty=difficulty,
    )

    interview_type = {
        "common": InterviewType.COMMON,
        "job": InterviewType.JOB,
        "mixed": InterviewType.COMPREHENSIVE,
    }[q_type]

    async with db.begin():
        interview = Interview(
            user_id=payload.user_id,
            category_id=category.job_category_id if category else None,
            interview_type=interview_type,
            total_questions=total_questions,
            current_question=0,
            status=0,
        )
        db.add(interview)
        await db.flush()

        questions_out: List[I_StartQ] = []
        for order, question in enumerate(random.sample(questions, len(questions)), start=1):
            answer = InterviewAnswer(i_id=interview.i_id, q_id=question.q_id, q_order=order)
            db.add(answer)
            questions_out.append(
                I_StartQ(
                    q_id=question.q_id,
                    q_order=order,
                    question_text=question.question_text,
                )
            )

    return I_StartRes(i_id=interview.i_id, questions=questions_out)
