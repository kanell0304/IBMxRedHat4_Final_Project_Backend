from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

# FastAPI 앱 생성
app = FastAPI(
    title="My FastAPI Application",
    description="API with separated service layer",
    version="1.0.0",
    lifespan=lifespan
)

# uvicorn app.main:app --port=8081 --reload
