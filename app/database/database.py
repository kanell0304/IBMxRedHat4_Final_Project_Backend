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
        from .models import community
        from .models import minigame
        from .models import roles
        from .models import user_roles

        Base.metadata.create_all(bind=sync_engine)

        # 기본 공통 질문
        from app.database.models.interview import InterviewQuestion, QuestionType
        from app.database.models.community import CommunityCategory
        default_common_questions = {
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

        with Session(sync_engine) as session:
            exists = session.query(InterviewQuestion).filter(InterviewQuestion.question_type == QuestionType.COMMON).count()
            if exists == 0:
                total_seeded = 0
                for lang, questions in default_common_questions.items():
                    for text in questions:
                        session.add(
                            InterviewQuestion(
                                category_id=None,
                                question_type=QuestionType.COMMON,
                                difficulty=None,
                                question_text=text,
                                language=lang,
                            )
                        )
                        total_seeded += 1
                session.commit()
                print(f"기본 공통 질문 {total_seeded}건 추가")

        # 기본 커뮤니티 카테고리
        default_categories = [
            {"name": "자유게시판", "description": "자유롭게 소통하는 공간"},
            {"name": "말투 상담소", "description": "말투와 커뮤니케이션을 상담하는 공간"},
            {"name": "취업·진로", "description": "면접 경험을 공유하는 공간"},
            {"name": "발표·주제 상담소", "description": "발표 준비하는 공간"},
        ]

        with Session(sync_engine) as session:
            created = 0
            for item in default_categories:
                exists = session.query(CommunityCategory).filter_by(category_name=item["name"]).first()
                if not exists:
                    session.add(CommunityCategory(category_name=item["name"], description=item["description"]))
                    created += 1
            if created:
                session.commit()
                print(f"기본 커뮤니티 카테고리 {created}건 추가")

        # 기본 Role 데이터 삽입
        from app.database.models.roles import Roles, RoleEnum
        
        default_roles = [
            {"role_name": RoleEnum.USER, "description": "일반 사용자"},
            {"role_name": RoleEnum.ADMIN, "description": "관리자"},
        ]
        
        with Session(sync_engine) as session:
            created = 0
            for item in default_roles:
                exists = session.query(Roles).filter_by(role_name=item["role_name"]).first()
                if not exists:
                    session.add(Roles(role_name=item["role_name"], description=item["description"]))
                    created += 1
            if created:
                session.commit()
                print(f"기본 Role {created}건 추가")

        print("데이터베이스 테이블 생성")
        
    except Exception as e:
        print(f"테이블 생성 실패: {e}")


def get_db_session():
    with Session(sync_engine) as session:
        yield session
