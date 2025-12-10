from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.core.settings import settings
from app.database.base import Base

# 엔진 설정
async_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    echo=False
)

sync_engine = create_engine(
    settings.sync_database_url,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db


def create_tables():
    try:
        # 모든 모델 import (Base에 등록하기 위해서임) # 여기 등록 안하면 테이블 생성이 안됨
        from .models import user
        from .models import communication
        from .models import image
        from .models import category
        from .models import presentation
        from .models import audio
        from .models import interview

        Base.metadata.create_all(bind=sync_engine)

        # 기본 공통 질문
        from app.database.models.interview import InterviewQuestion, QuestionType
        default_common_questions = [
            "자기소개를 해주세요.",
            "지원 동기를 말씀해주세요.",
            "본인의 강점과 약점을 설명해주세요.",
            "최근 성취한 일과 그 과정에서의 역할을 말해주세요.",
            "입사 후 목표와 계획을 알려주세요.",
            "갈등 상황을 어떻게 해결했는지 사례를 들어 주세요.",
            "스트레스를 관리하는 방법을 말해주세요.",
        ]

        with Session(sync_engine) as session:
            exists = session.query(InterviewQuestion).filter(InterviewQuestion.question_type == QuestionType.COMMON).count()
            if exists == 0:
                for text in default_common_questions:
                    session.add(
                        InterviewQuestion(
                            category_id=None,
                            question_type=QuestionType.COMMON,
                            difficulty=None,
                            question_text=text,
                        )
                    )
                session.commit()
                print(f"기본 공통 질문 {len(default_common_questions)}건 추가")

        print("데이터베이스 테이블 생성")
        
    except Exception as e:
        print(f"테이블 생성 실패: {e}")