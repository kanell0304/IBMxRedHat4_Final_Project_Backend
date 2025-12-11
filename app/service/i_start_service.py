import random
from typing import List, Optional
from sqlalchemy import select
from app.database.crud.category import create_jobcategory
from app.database.models.category import JobCategory
from app.database.models.interview import Interview, InterviewAnswer, InterviewQuestion, InterviewType, QuestionType, DifficultyLevel
from app.database.schemas.interview import I_StartReq, I_StartRes, I_StartQ
from app.core.settings import settings
from openai import AsyncOpenAI
import json


QUESTION_TYPE_ALIAS = {
    "공통질문만": "common",
    "직무관련": "job",
    "섞어서": "mixed",
}

LLM_JOB_CATEGORIES = {"백엔드개발"}


def norm_q_type(question_type: str) -> str:
    key = (question_type or "").strip()
    if key in QUESTION_TYPE_ALIAS:
        return QUESTION_TYPE_ALIAS[key]

    lowered = key.lower()
    if lowered in ("common", "job", "mixed"):
        return lowered

    raise ValueError("question_type은 common | job | mixed 중 하나여야 합니다.")


def is_llm_job(job_role: Optional[str]) -> bool:
    if not job_role:
        return False
    lowered = job_role.strip().lower()
    return lowered in LLM_JOB_CATEGORIES


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

    # 없으면 생성하여 기본 카테고리로 사용
    return await create_jobcategory(db, job_category_name=job_role)

COMMON_QUESTIONS = {
    "ko": [
        "자기소개를 해주세요.",
        "지원 동기를 말씀해주세요.",
        "본인의 강점과 약점을 설명해주세요.",
        "최근 성취한 일과 그 과정에서의 역할을 말해주세요.",
        "입사 후 목표와 계획을 알려주세요.",
        "갈등 상황을 어떻게 해결했는지 사례를 들어 주세요.",
        "스트레스를 관리하는 방법을 말해주세요.",
    ],
    "en": [
        "please tell us about yourself briefly",
        "What motivated you to apply for this role?",
        "Why should we hire you?",
        "What are you passionate about?",
        "What are your greatest strengths?",
        "What are your weaknesses?",
        "what is your greatest accomplishment in life?",
        "What are your furture goal? in life and in career?",
        "Where do you see yourself in five years?",
        "How do you handle conflict in the workplace?",
        "How do you manage stress?",
        "Do you have any questions for us?",
    ],
}


def job_questions(job_role: str, language: str) -> List[str]:
    lang = (language or "ko").lower()
    role = job_role or ("applied role" if lang == "en" else "지원 직무")
    if lang == "en":
        return [
            f"What core competencies does a {role} need, and how have you built them?",
            f"Walk me through a recent {role} project and the impact you had.",
            f"What was the hardest technical or business issue in your {role} work, and how did you resolve it?",
            f"How do you define and track success metrics as a {role}?",
            f"How do you stay current with {role}-related trends or tech? Give a concrete example.",
            f"Tell me about a setback in your {role} work and what you learned from it.",
        ]
    return [
        f"{role} 역할에서 중요하다고 생각하는 역량은 무엇이며, 이를 어떻게 발전시켜 왔나요?",
        f"최근 수행한 {role} 관련 프로젝트/업무를 설명하고, 본인의 기여도를 구체적으로 말해주세요.",
        f"{role} 업무에서 직면했던 가장 큰 기술적/비즈니스적 문제와 해결 과정을 설명해주세요.",
        f"{role}로서 성과를 측정하는 지표나 기준을 어떻게 설정하고 관리했는지 알려주세요.",
        f"{role} 관련 최신 트렌드나 기술을 어떻게 학습하고 적용했는지 사례를 들어 주세요.",
        f"{role} 업무에서 실패하거나 어려웠던 사례를 공유하고, 배운 점을 설명해주세요.",
    ]


async def job_selection_llm(total: int, difficulty: Optional[DifficultyLevel], language: str) -> List[str]:
    if not settings.openai_api_key:
        raise ValueError("API 키가 설정 안됨")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    target_total = max(1, total)
    max_len = 30
    diff_text = {DifficultyLevel.EASY: "easy", DifficultyLevel.MID: "mid", DifficultyLevel.HARD: "hard", None: "mixed"}.get(difficulty, "mixed")
    prompt = f"Generate {target_total} backend interview questions in {language}. Max {max_len} characters per question. No numbering. Difficulty: {diff_text}. Return JSON array of strings."
    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You create very short interview questions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        content = resp.choices[0].message.content or "[]"
        questions = json.loads(content)
        if not isinstance(questions, list):
            raise ValueError("LLM 응답이 리스트 형식이 아닙니다.")
    except Exception as e:
        raise ValueError(f"백엔드 질문 생성 실패: {e}")

    cleaned: List[str] = []
    seen = set()
    for q in questions:
        text = str(q).strip().strip('"').strip("'")
        if not text or text in seen:
            continue
        if len(text) > max_len:
            text = text[:max_len]
        cleaned.append(text)
        seen.add(text)
        if len(cleaned) >= target_total:
            break

    if len(cleaned) < target_total:
        raise ValueError("충분한 백엔드 질문을 생성하지 못했습니다.")
    return cleaned

async def add_common_questions(db, total: int, difficulty: Optional[DifficultyLevel], language: str):
    created: List[InterviewQuestion] = []
    pool = COMMON_QUESTIONS.get((language or "ko").lower(), COMMON_QUESTIONS["ko"])
    for text in pool[: total]:
        q = InterviewQuestion(
            category_id=None,
            question_type=QuestionType.COMMON,
            difficulty=difficulty,
            question_text=text,
            language=(language or "ko").lower(),
        )
        db.add(q)
        created.append(q)
    await db.flush()
    return created


async def add_q(
    db, category_id: int, job_role: str, total: int, difficulty: Optional[DifficultyLevel], language: str
):
    created: List[InterviewQuestion] = []
    for text in job_questions(job_role, language)[: total]:
        q = InterviewQuestion(
            category_id=category_id,
            question_type=QuestionType.JOB,
            difficulty=difficulty,
            question_text=text,
            language=(language or "ko").lower(),
        )
        db.add(q)
        created.append(q)
    await db.flush()
    return created


async def load_q(db, question_type: str, category_id: Optional[int], total_questions: int, difficulty: Optional[DifficultyLevel], job_role: Optional[str], language: str):
    def _apply_difficulty(query):
        if difficulty:
            return query.where(InterviewQuestion.difficulty == difficulty)
        return query

    # 영어는 공통 질문만 허용
    if language == "en" and question_type != "common":
        raise ValueError("English interviews support common questions only.")

    if question_type == "common":
        query = select(InterviewQuestion).where(
            InterviewQuestion.question_type == QuestionType.COMMON,
            InterviewQuestion.language == language,
        )
        result = await db.execute(_apply_difficulty(query))
        commons = result.scalars().all()
        if len(commons) < total_questions:
            await add_common_questions(db, total=total_questions - len(commons), difficulty=difficulty, language=language)
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
            InterviewQuestion.language == language,
        )
        result = await db.execute(_apply_difficulty(query))
        jobs = result.scalars().all()
        if len(jobs) < total_questions:
            await add_q(
                db,
                category_id=category_id,
                job_role=job_role or "",
                total=total_questions - len(jobs),
                difficulty=difficulty,
                language=language,
            )
            result = await db.execute(_apply_difficulty(query))
            jobs = result.scalars().all()
        if len(jobs) < total_questions:
            raise ValueError("해당 직무 질문 수가 충분하지 않습니다.")
        return random.sample(jobs, total_questions)

    # mixed
    if not category_id:
        raise ValueError("섞어서 선택 시 직무 정보를 함께 전달해주세요.")

    common_query = select(InterviewQuestion).where(
        InterviewQuestion.question_type == QuestionType.COMMON,
        InterviewQuestion.language == language,
    )
    job_query = select(InterviewQuestion).where(
        InterviewQuestion.question_type == QuestionType.JOB,
        InterviewQuestion.category_id == category_id,
        InterviewQuestion.language == language,
    )

    common_result = await db.execute(_apply_difficulty(common_query))
    job_result = await db.execute(_apply_difficulty(job_query))
    commons = common_result.scalars().all()
    jobs = job_result.scalars().all()

    if len(commons) + len(jobs) < total_questions:
        if len(commons) < total_questions:
            await add_common_questions(db, total=total_questions - len(commons), difficulty=difficulty, language=language)
            common_result = await db.execute(_apply_difficulty(common_query))
            commons = common_result.scalars().all()
        if len(jobs) < total_questions:
            await add_q(
                db,
                category_id=category_id,
                job_role=job_role or "",
                total=total_questions - len(jobs),
                difficulty=difficulty,
                language=language,
            )
            job_result = await db.execute(_apply_difficulty(job_query))
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


async def start_interview_session(db, payload: I_StartReq) -> I_StartRes:
    q_type = norm_q_type(payload.question_type)
    total_questions = payload.total_questions or 5
    language = (payload.language or "ko").lower()

    interview_type = {
        "common": InterviewType.COMMON,
        "job": InterviewType.JOB,
        "mixed": InterviewType.COMPREHENSIVE,
    }[q_type]

    async with db.begin():
        category: Optional[JobCategory] = None
        if q_type in ("job", "mixed"):
            category = await get_jobcat(db, payload.job_role)

        # 공통질문만 선택 시 난이도는 무시
        difficulty = None if q_type == "common" else norm_diff(payload.difficulty)

        use_backend_llm = q_type == "job" and is_llm_job(payload.job_role)

        if use_backend_llm:
            # 백엔드 직무는 LLM으로 즉석 생성
            q_texts = await job_selection_llm(total_questions, difficulty, language)
            questions: List[InterviewQuestion] = []
            for text in q_texts:
                q = InterviewQuestion(
                    category_id=category.job_category_id if category else None,
                    question_type=QuestionType.JOB,
                    difficulty=difficulty,
                    question_text=text,
                    language=language,
                )
                db.add(q)
                questions.append(q)
            await db.flush()
        else:
            cat_id = category.job_category_id if category else None
            questions = await load_q(db, q_type, cat_id, total_questions, difficulty, payload.job_role, language)

        interview = Interview(
            user_id=payload.user_id,
            category_id=category.job_category_id if category else None,
            interview_type=interview_type,
            total_questions=total_questions,
            current_question=0,
            status=0,
            language=language,
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

    return I_StartRes(i_id=interview.i_id, questions=questions_out, language=language)