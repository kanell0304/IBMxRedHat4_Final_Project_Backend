from ..base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import String, func, DateTime, Integer, ForeignKey
from typing import Optional, List

# 사용자 테이블
class Presentation(Base):
    __tablename__="presentation"

    pr_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    pr_title: Mapped[str] = mapped_column(String(100), nullable=False)
    pr_description: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    # category_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)


    user: Mapped["User"] = relationship("User", back_populates="presentation")
