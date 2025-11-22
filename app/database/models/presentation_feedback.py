from ..base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import String, func, DateTime, Integer, ForeignKey, Float
from typing import Optional, List

# 사용자 테이블
class PresentationFeedback(Base):
    __tablename__="presentation_feedback"

    pf_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    simple_feedback: Mapped[str] = mapped_column(String(100), nullable=False)
    detail_feedback: Mapped[str] = mapped_column(String(100), nullable=False)
    voice_size: Mapped[float] = mapped_column(Float, nullable=False)
    voice_speed: Mapped[float] = mapped_column(Float, nullable=False)
    speech_rate: Mapped[float] = mapped_column(Float, nullable=False)
    silence_duration: Mapped[float] = mapped_column(Float, nullable=False)
    pr_id: Mapped[int] = mapped_column(ForeignKey('presentation.pr_id'), nullable=False)

    presentation: Mapped["Presentation"] = relationship("Presentation", back_populates="presentation_feedback")