from sqlalchemy import DateTime, ForeignKey, String, Integer, Text, func, UniqueConstraint, Index
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


# 커뮤니티 카테고리 테이블
class CommunityCategory(Base):
    __tablename__ = "community_categories"
    
    category_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # 예: 발표 후기, 면접 후기, 자유게시판
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 카테고리 설명
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계
    posts: Mapped[List["CommunityPost"]] = relationship("CommunityPost", back_populates="category", cascade="all, delete-orphan")


# 커뮤니티 게시글 테이블
class CommunityPost(Base):
    __tablename__ = "community_posts"
    
    post_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)  # 작성자
    category_id: Mapped[int] = mapped_column(ForeignKey("community_categories.category_id", ondelete="CASCADE"), nullable=False)  # 카테고리
    title: Mapped[str] = mapped_column(String(200), nullable=False)  # 제목
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 내용
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 조회수
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 좋아요 수
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 댓글 수
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 작성일
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)  # 수정일
    
    # 관계
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    category: Mapped["CommunityCategory"] = relationship("CommunityCategory", back_populates="posts")
    comments: Mapped[List["CommunityComment"]] = relationship("CommunityComment", back_populates="post", cascade="all, delete-orphan")
    likes: Mapped[List["CommunityPostLike"]] = relationship("CommunityPostLike", back_populates="post", cascade="all, delete-orphan")
    
    # 인덱스 설정 (성능 최적화)
    __table_args__ = (
        Index('idx_category_created', 'category_id', 'created_at'),  # 카테고리별 최신순 조회
        Index('idx_user_created', 'user_id', 'created_at'),  # 사용자별 게시글 조회
    )


# 커뮤니티 댓글 테이블 (대댓글 포함)
class CommunityComment(Base):
    __tablename__ = "community_comments"
    
    comment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("community_posts.post_id", ondelete="CASCADE"), nullable=False)  # 게시글 ID
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)  # 댓글 작성자
    parent_comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("community_comments.comment_id", ondelete="CASCADE"), nullable=True)  # 부모 댓글 (NULL이면 일반 댓글, 값이 있으면 대댓글)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 댓글 내용
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)  # 작성일
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)  # 수정일
    
    # 관계
    post: Mapped["CommunityPost"] = relationship("CommunityPost", back_populates="comments")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    
    # Self-referencing 관계 (대댓글) - 자기 테이블의 값을 부모관계로 둠
    parent_comment: Mapped[Optional["CommunityComment"]] = relationship("CommunityComment", remote_side=[comment_id], back_populates="replies")
    replies: Mapped[List["CommunityComment"]] = relationship("CommunityComment", back_populates="parent_comment", cascade="all, delete-orphan")
    
    # 인덱스 설정
    __table_args__ = (
        Index('idx_post_created', 'post_id', 'created_at'),  # 게시글별 댓글 조회
        Index('idx_parent_comment', 'parent_comment_id'),  # 대댓글 조회
    )


# 게시글 좋아요 테이블 (중복 방지)
class CommunityPostLike(Base):
    __tablename__ = "community_post_likes"
    
    like_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("community_posts.post_id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    # 관계
    post: Mapped["CommunityPost"] = relationship("CommunityPost", back_populates="likes")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    
    # 유니크 제약 조건 (한 사용자가 같은 게시글에 중복 좋아요 방지)
    __table_args__ = (
        UniqueConstraint('post_id', 'user_id', name='uq_post_user_like'),
        Index('idx_user_likes', 'user_id'),  # 사용자가 좋아요한 게시글 조회
    )
