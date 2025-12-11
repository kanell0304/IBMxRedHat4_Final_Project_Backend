from typing import Optional

from pydantic import BaseModel


class MainCategoryResponse(BaseModel):
    m_category_id: int
    m_category_name: str

    class Config:
        from_attributes = True


class JobCategoryResponse(BaseModel):
    job_category_id: int
    job_category_name: str
    m_category_id: Optional[int] = None

    class Config:
        from_attributes = True
