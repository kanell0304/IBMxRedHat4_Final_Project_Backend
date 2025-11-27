from sqlalchemy import Boolean, DateTime, ForeignKey, String, Integer, func
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


class Interview(Base):
    __tablename__ = "interviews"
    interview_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("job_categories.job_category_id"), nullable=False)
    total_duration: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    answers: Mapped[List["InterviewAnswer"]] = relationship("InterviewAnswer", cascade="all, delete-orphan")
    results: Mapped[List["InterviewResult"]] = relationship("InterviewResult", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "i_question"
    i_question_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    common_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    job_question_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_questions.job_question_id"), nullable=True)
    job_question_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class InterviewAnswer(Base):
    __tablename__ = "i_answers"
    i_answer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    results: Mapped[List["InterviewResult"]] = relationship("InterviewResult")


class InterviewResult(Base):
    __tablename__ = "i_result"
    i_result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.interview_id"), nullable=False)
    script_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    i_question_id: Mapped[Optional[int]] = mapped_column(ForeignKey("i_question.i_question_id"), nullable=True)
    i_answer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("i_answers.i_answer_id"), nullable=True)
    formal: Mapped[Optional[int]] = mapped_column(nullable=True)
    sentence_speed: Mapped[Optional[int]] = mapped_column(nullable=True)
    clarity: Mapped[Optional[int]] = mapped_column(nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    advice: Mapped[Optional[str]] = mapped_column(String, nullable=True)
