from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.category import list_job_categories, list_main_categories
from app.database.database import get_db
from app.database.schemas.category import JobCategoryResponse, MainCategoryResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/main", response_model=list[MainCategoryResponse])
async def get_main_categories(db: AsyncSession = Depends(get_db)):
    return await list_main_categories(db)


@router.get("/category", response_model=list[JobCategoryResponse])
async def get_job_categories(
    m_category_id: int | None = Query(default=None, description="선택적으로 상위 카테고리로 필터링"),
    db: AsyncSession = Depends(get_db),
):
    return await list_job_categories(db, m_category_id)
