from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 카테고리 스키마 ====================
class CommunityCategoryBase(BaseModel):
    category_name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class CommunityCategoryCreate(CommunityCategoryBase):
    pass


class CommunityCategoryResponse(CommunityCategoryBase):
    category_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 게시글 스키마 ====================
class CommunityPostBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: str


class CommunityPostCreate(CommunityPostBase):
    category_id: int


class CommunityPostUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None


class CommunityPostResponse(CommunityPostBase):
    post_id: int
    user_id: int
    category_id: int
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime
    
    # 추가 정보
    author_nickname: Optional[str] = None
    category_name: Optional[str] = None
    is_liked: Optional[bool] = None  # 현재 사용자가 좋아요를 눌렀는지
    
    class Config:
        from_attributes = True


class CommunityPostListResponse(BaseModel):
    post_id: int
    user_id: int
    category_id: int
    title: str
    view_count: int
    like_count: int
    comment_count: int
    created_at: datetime
    
    # 추가 정보
    author_nickname: Optional[str] = None
    category_name: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==================== 댓글 스키마 ====================
class CommunityCommentBase(BaseModel):
    content: str


class CommunityCommentCreate(CommunityCommentBase):
    parent_comment_id: Optional[int] = None


class CommunityCommentUpdate(BaseModel):
    content: str


class CommunityCommentResponse(CommunityCommentBase):
    comment_id: int
    post_id: int
    user_id: int
    parent_comment_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    # 추가 정보
    author_nickname: Optional[str] = None
    replies: Optional[List["CommunityCommentResponse"]] = []
    
    class Config:
        from_attributes = True


# Self-referencing을 위한 model_rebuild
CommunityCommentResponse.model_rebuild()


# ==================== 좋아요 스키마 ====================
class CommunityPostLikeResponse(BaseModel):
    like_id: int
    post_id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
