from sqlalchemy import DateTime, ForeignKey, String, Integer, func, Text, JSON, LargeBinary
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from enum import Enum
from sqlalchemy import Enum as SQLEnum


# 인터뷰 타입 : 공통 or 직무 or 종합(둘 다)
class InterviewType(str, Enum):
  COMMON="common"
  JOB="job"
  COMPREHENSIVE="comprehensive"

#인터뷰 기본정보
class Interview(Base):
  __tablename__ = "interviews"

  i_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
  category_id: Mapped[int] = mapped_column(ForeignKey("job_categories.job_category_id"), nullable=True)  # 직무 카테고리
  language: Mapped[str] = mapped_column(String(3), nullable=False, default="ko")  # 질문/세션 언어
  created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
  deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # 손봐야함
  status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 진행 상태(예: 0-대기, 1-진행, 2-완료) # 구현 할지 안할지는 미정
  total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)  # 진행할 질문 수(기본 5)
  current_question: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 현재 진행 중인 질문 순번
  interview_type: Mapped[InterviewType] = mapped_column(SQLEnum(InterviewType), nullable=False)

  answers: Mapped[List["InterviewAnswer"]] = relationship("InterviewAnswer", back_populates="interview", cascade="all, delete-orphan")
  results: Mapped[List["InterviewResult"]] = relationship("InterviewResult", back_populates="interview", cascade="all, delete-orphan")  # llm 결과


# 질문 타입 : 공통 or 직무
class QuestionType(str, Enum):
  COMMON="common"
  JOB="job"

# 질문 난이도
class DifficultyLevel(str, Enum):
  EASY="easy"
  MID="mid"
  HARD="hard"

# 인터뷰에서 사용할 질문 (공통/직무별)
class InterviewQuestion(Base):
  __tablename__ = "i_questions"

  q_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  # 공통 질문이면 null, 직무 질문이면 FK
  category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_categories.job_category_id"), nullable=True)
  language: Mapped[str] = mapped_column(String(3), nullable=False, default="ko", server_default="ko")
  question_type: Mapped[QuestionType] = mapped_column(SQLEnum(QuestionType), nullable=False)
  difficulty: Mapped[Optional[DifficultyLevel]] = mapped_column(SQLEnum(DifficultyLevel), nullable=True)
  question_text: Mapped[str] = mapped_column(String(500), nullable=False)


#사용자가 제출한 인터뷰 답변
class InterviewAnswer(Base):
  __tablename__ = "i_answers"

  i_answer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  i_id: Mapped[int] = mapped_column(ForeignKey("interviews.i_id"), nullable=False, index=True)
  q_id: Mapped[Optional[int]] = mapped_column(ForeignKey("i_questions.q_id"), nullable=True)
  q_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 질문 순서(1~5)
  duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 질문당 소요시간
  transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # STT 텍스트
  labels_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # BERT 분류 결과 저장
  stt_metrics_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
  created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
  deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

  results: Mapped[List["InterviewResult"]] = relationship("InterviewResult", cascade="all, delete-orphan")  # 세부 평가/결과
  interview: Mapped["Interview"] = relationship("Interview", back_populates="answers")  # 인터뷰 역참조


class ResultScope(str, Enum):
  OVERALL="overall"
  PER_QUESTION="per_question"
  

#각 답변/질문에 대한 평가/요약 결과
class InterviewResult(Base):
  __tablename__ = "i_results"

  i_result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
  user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
  i_id: Mapped[int] = mapped_column(ForeignKey("interviews.i_id"), nullable=False)
  q_id: Mapped[Optional[int]] = mapped_column(ForeignKey("i_questions.q_id"), nullable=True)
  i_answer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("i_answers.i_answer_id"), nullable=True)
  
  scope: Mapped[ResultScope] = mapped_column(SQLEnum(ResultScope), nullable=False, default=ResultScope.OVERALL)
  report: Mapped[dict] = mapped_column(JSON, nullable=False)
  created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
  deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

  interview:Mapped["Interview"]=relationship("Interview", back_populates="results")
  answer:Mapped[Optional["InterviewAnswer"]]=relationship("InterviewAnswer", back_populates="results")
