from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import create_engine
from backend.app.core.settings import settings
from backend.app.database.base import Base

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
        # 모든 모델 import (Base에 등록하기 위해)
        import backend.app.database.models.user
        import backend.app.database.models.roles
        import backend.app.database.models.user_roles
        import backend.app.database.models.surveys
        import backend.app.database.models.survey_question
        import backend.app.database.models.survey_option
        import backend.app.database.models.responses
        import backend.app.database.models.response_detail
        import backend.app.database.models.surveystats
        import backend.app.database.models.email_logs
        import backend.app.database.models.image  # image 모델 추가

        Base.metadata.create_all(bind=sync_engine)
        print("데이터베이스 테이블 생성")
        
    except Exception as e:
        print(f"테이블 생성 실패: {e}")
