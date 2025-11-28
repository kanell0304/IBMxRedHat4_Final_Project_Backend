from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.database import models
from app.database.database import async_engine, Base
from app.routers import communication
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

# # 로드시 테이블 자동생성
# @asynccontextmanager
# async def lifespan(app:FastAPI):
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield
#     await async_engine.dispose()

app = FastAPI()

# CORS 설정 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #모든 도메인 / 안되면 "http://localhost:3000" 변경
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#라우터 등록
app.include_router(communication.router)