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


async def create_jobcategory(db, job_category_name: str, main_category_name: Optional[str] = None):
  existing = await db.execute(
    select(JobCategory).where(
      JobCategory.job_category_name == job_category_name
    )
  )
  cat = existing.scalars().first()
  if cat:
    return cat

  main_category_id = None
  if main_category_name:
    main = await db.execute(select(MainCategory).where(MainCategory.m_category_name == main_category_name))
    main_obj = main.scalars().first()
    if main_obj:
      main_category_id = main_obj.m_category_id

  new_category = JobCategory(job_category_name=job_category_name, m_category_id=main_category_id)
  db.add(new_category)
  await db.flush()  # job_category_id 확보
  return new_category
