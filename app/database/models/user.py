from sqlalchemy import Integer, String, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base
from typing import Optional, List
from datetime import datetime

class User(Base):
    __tablename__="users"

    user_id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False) # 이메일(아이디)
    username: Mapped[str] = mapped_column(String(40), nullable=False) # 이름
    nickname: Mapped[str] = mapped_column(String(40), nullable=False) # 닉네임
    password: Mapped[Optional[str]] = mapped_column(String(300), nullable=True) # 비밀번호 (소셜 로그인은 비밀번호 없음)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # 전화번호 (소셜 로그인은 선택)
    profile_image_id: Mapped[Optional[int]] = mapped_column(Integer,ForeignKey("images.id", ondelete="SET NULL"),nullable=True) # 유저 프로필 이미지
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 생성일(회원가입일)
    refresh_token:Mapped[Optional[str]] = mapped_column(String(300), nullable=True) # 리프레쉬 토큰 정보
    is_social: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0: 일반 회원가입, 1: 소셜 회원가입
    social_provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 어떤 소셜인지 ex) kakao, google (kakao 만 할거임)
    social_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 소셜 플랫폼의 고유 id - user_id와 별개로 그쪽에서 지정하는 고유 id
    reset_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)  # 비밀번호 재설성 인증 코드 6자리
    reset_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # 인증 코드 유효 시간

    #1:M관계
    # presentations: Mapped[List["Presentation"]] = relationship("Presentation", back_populates="user", cascade="all, delete-orphan")
    communications: Mapped[list["Communication"]] = relationship("Communication", back_populates="user", cascade="all, delete-orphan")
    profile_image: Mapped[Optional["Image"]] = relationship("Image", foreign_keys=[profile_image_id])
    
    # 커뮤니티 관계
    community_posts: Mapped[List["CommunityPost"]] = relationship("CommunityPost", back_populates="user", cascade="all, delete-orphan")
    community_comments: Mapped[List["CommunityComment"]] = relationship("CommunityComment", back_populates="user", cascade="all, delete-orphan")
    community_likes: Mapped[List["CommunityPostLike"]] = relationship("CommunityPostLike", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_email', 'email'),  # 로그인 시 이메일로 사용자 조회
        Index('idx_social_id', 'social_provider', 'social_id'),  # 소셜 로그인 조회용
    )

    roles: Mapped[List["Roles"]] = relationship("Roles", secondary="user_roles", back_populates="users")
