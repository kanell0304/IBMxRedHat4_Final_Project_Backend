from sqlalchemy import DateTime, ForeignKey, String, Integer, func
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


class Communication(Base):
    __tablename__ = "communication"
    c_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    c_title: Mapped[str] = mapped_column(String(100), nullable=False)
    c_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)

    results: Mapped[List["CommunicationResult"]] = relationship("CommunicationResult", cascade="all, delete-orphan", back_populates="communication")


class CommunicationResult(Base):
    __tablename__ = "c_result"
    c_result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(ForeignKey("communication.c_id"), nullable=False)
    # created at 삭제 (communication 테이블에 있음)
    sentence_speed: Mapped[Optional[int]] = mapped_column(nullable=True)
    silence: Mapped[Optional[int]] = mapped_column(nullable=True)
    filler: Mapped[Optional[int]] = mapped_column(nullable=True)
    curse: Mapped[Optional[int]] = mapped_column(nullable=True)
    clearly_meaning: Mapped[Optional[int]] = mapped_column(nullable=True)
    clarity: Mapped[Optional[int]] = mapped_column(nullable=True)
    cut: Mapped[Optional[int]] = mapped_column(nullable=True)
    feedback_body: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    communication: Mapped["Communication"] = relationship("Communication", back_populates="results")
