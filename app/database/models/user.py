from sqlalchemy import Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base
from typing import Optional
from datetime import datetime

class User(Base):
    __tablename__="users"

    user_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False) # 이메일(아이디)
    username: Mapped[str] = mapped_column(String(40), nullable=False) # 이름
    nickname: Mapped[str] = mapped_column(String(40), nullable=False) # 닉네임
    password: Mapped[str] = mapped_column(String(300), nullable=False) # 비밀번호
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False) # 전화번호
    profile_image_id: Mapped[Optional[int]] = mapped_column(Integer,ForeignKey("images.id", ondelete="SET NULL"),nullable=True) # 유저 프로필 이미지
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 생성일(회원가입일)
    refresh_token:Mapped[Optional[str]] = mapped_column(String(300), nullable=True) # 리프레쉬 토큰 정보

    #1:M관계
    # presentations: Mapped[List["Presentation"]] = relationship("Presentation", back_populates="user", cascade="all, delete-orphan")
    communications: Mapped[list["Communication"]] = relationship("Communication", back_populates="user", cascade="all, delete-orphan")
    profile_image: Mapped[Optional["Image"]] = relationship("Image", foreign_keys=[profile_image_id])

    __table_args__ = (
    Index('idx_email', 'email'),  # 로그인 시 이메일로 사용자 조회
    )
