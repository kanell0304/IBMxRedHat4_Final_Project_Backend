from sqlalchemy import ForeignKey, String
from app.database.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


class MainCategory(Base):
    __tablename__ = "main_category"

    m_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    m_category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    communications: Mapped[List["Communication"]] = relationship("Communication", back_populates="main_category")
    presentations: Mapped[List["Presentation"]] = relationship("Presentation", back_populates="main_category")
    job_categories: Mapped[List["JobCategory"]] = relationship("JobCategory")


class JobCategory(Base):
    __tablename__ = "job_categories"

    job_category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_category_name: Mapped[str] = mapped_column(String(100), nullable=False) # 직무 카테고리 이름
    m_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("main_category.m_category_id"), nullable=True)
    job_questions: Mapped[List["JobQuestion"]] = relationship("JobQuestion", cascade="all, delete-orphan") # 직무별 질문 리스트
    interviews: Mapped[List["Interview"]] = relationship("Interview", cascade="all, delete-orphan") # 해당 카테고리로 생성된


class JobQuestion(Base):
    __tablename__ = "job_questions"
    
    job_q_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_categories.job_category_id"), nullable=True) # 소속 직무 카테고리
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)