from typing import List, Optional

from sqlalchemy import select

from app.database.models.category import JobCategory, MainCategory


async def list_main_categories(db) -> List[MainCategory]:
  result = await db.execute(select(MainCategory))
  return result.scalars().all()


async def list_job_categories(db, m_category_id: Optional[int] = None) -> List[JobCategory]:
  query = select(JobCategory)
  if m_category_id is not None:
    query = query.where(JobCategory.m_category_id == m_category_id)

  result = await db.execute(query)
  return result.scalars().all()


async def get_jobcategory(
  db, *, job_category_name: str, main_category_name: Optional[str] = None
) -> Optional[JobCategory]:
  query = select(JobCategory)
  if main_category_name:
    query = query.join(MainCategory, JobCategory.m_category_id == MainCategory.m_category_id)
    query = query.where(
      MainCategory.m_category_name == main_category_name,
      JobCategory.job_category_name == job_category_name,
    )
  else:
    query = query.where(JobCategory.job_category_name == job_category_name)

  result = await db.execute(query)
  return result.scalars().first()
