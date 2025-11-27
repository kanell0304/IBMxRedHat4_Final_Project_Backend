from sqlalchemy import ForeignKey, String
from app.database.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


class MainCategory(Base):
    __tablename__ = "main_category"
    m_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    m_category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    communications: Mapped[List["Communication"]] = relationship("Communication")
    presentations: Mapped[List["Presentation"]] = relationship("Presentation")
    job_categories: Mapped[List["JobCategory"]] = relationship("JobCategory")


class JobCategory(Base):
    __tablename__ = "job_categories"
    job_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    m_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("main_category.m_category_id"), nullable=True)
    job_questions: Mapped[List["JobQuestion"]] = relationship("JobQuestion")
    interviews: Mapped[List["Interview"]] = relationship("Interview")
