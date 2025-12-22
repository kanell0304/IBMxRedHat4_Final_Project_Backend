from fastapi import APIRouter, Depends, HTTPException, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from ..database.database import get_db
from ..database.crud.community import CommunityCRUD
from ..database.models.community import CommunityComment
from ..database.schemas.community import (CommunityCategoryCreate, CommunityCategoryResponse, CommunityPostCreate, CommunityPostUpdate, CommunityPostResponse, CommunityPostListResponse, CommunityCommentCreate, CommunityCommentUpdate, CommunityCommentResponse)
from fastapi import APIRouter, Depends, HTTPException, status, Cookie

router = APIRouter(prefix="/community", tags=["Community"])

# 모든 카테고리 조회
@router.get("/categories", response_model=List[CommunityCategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    categories = await CommunityCRUD.get_all_categories(db)
    return categories

# 카테고리 생성 (관리자용)
@router.post("/categories", response_model=CommunityCategoryResponse)
async def create_category(category_name: str = Form(...), description: Optional[str] = Form(None), db: AsyncSession = Depends(get_db)):
    category = await CommunityCRUD.create_category(db, category_name, description)
    return category

# 게시글 작성
@router.post("/posts", response_model=CommunityPostResponse)
async def create_post(user_id: int = Form(...), category_id: int = Form(...), title: str = Form(...), content: str = Form(...), db: AsyncSession = Depends(get_db)):
    # 이미 카테고리가 존재하는지 확인
    category = await CommunityCRUD.get_category_by_id(db, category_id)

    if not category: # 이미 있으면 오류 메세지 발생
        raise HTTPException(status_code=404, detail="Category not found")
    
    post = await CommunityCRUD.create_post(db, user_id, category_id, title, content)
    
    # 응답 데이터 조회 (작성자, 카테고리 정보 포함)
    post_detail = await CommunityCRUD.get_post_by_id(db, post.post_id)
    
    return CommunityPostResponse(
        post_id=post_detail.post_id,
        user_id=post_detail.user_id,
        category_id=post_detail.category_id,
        title=post_detail.title,
        content=post_detail.content,
        view_count=post_detail.view_count,
        like_count=post_detail.like_count,
        comment_count=post_detail.comment_count,
        created_at=post_detail.created_at,
        updated_at=post_detail.updated_at,
        author_nickname=post_detail.user.nickname if post_detail.user else None,
        category_name=post_detail.category.category_name if post_detail.category else None
    )

# 게시글 목록 조회(페이징)
@router.get("/posts", response_model=dict)
async def get_posts(category_id: Optional[int] = Query(None), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), order_by: str = Query("latest", regex="^(latest|popular|views)$"), db: AsyncSession = Depends(get_db)):

    skip = (page - 1) * page_size
    posts, total = await CommunityCRUD.get_posts(db, category_id, skip, page_size, order_by)
    
    posts_data = [
        CommunityPostListResponse(
            post_id=post.post_id,
            user_id=post.user_id,
            category_id=post.category_id,
            title=post.title,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            created_at=post.created_at,
            author_nickname=post.user.nickname if post.user else None,
            category_name=post.category.category_name if post.category else None
        )
        for post in posts
    ]
    
    return {
        "success": True,
        "data": posts_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

# 게시글 상세 조회 (조회수 증가)
@router.get("/posts/{post_id}", response_model=dict)
async def get_post(post_id: int, user_id: Optional[int] = Query(None), increment_view: bool = Query(True), db: AsyncSession = Depends(get_db)):
    post = await CommunityCRUD.get_post_by_id(db, post_id, increment_view=increment_view)
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 사용자가 좋아요를 눌렀는지 확인
    is_liked = False
    if user_id:
        is_liked = await CommunityCRUD.check_user_liked(db, post_id, user_id)
    
    # 댓글 데이터 변환
    comments_data = []
    for comment in post.comments:
        if comment.parent_comment_id is None:  # 부모 댓글만
            comment_dict = CommunityCommentResponse(
                comment_id=comment.comment_id,
                post_id=comment.post_id,
                user_id=comment.user_id,
                parent_comment_id=comment.parent_comment_id,
                content=comment.content,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                author_nickname=comment.user.nickname if comment.user else None,
                replies=[
                    CommunityCommentResponse(
                        comment_id=reply.comment_id,
                        post_id=reply.post_id,
                        user_id=reply.user_id,
                        parent_comment_id=reply.parent_comment_id,
                        content=reply.content,
                        created_at=reply.created_at,
                        updated_at=reply.updated_at,
                        author_nickname=reply.user.nickname if reply.user else None
                    )
                    for reply in comment.replies
                ]
            )
            comments_data.append(comment_dict)
    
    return {
        "success": True,
        "data": {
            "post": CommunityPostResponse(
                post_id=post.post_id,
                user_id=post.user_id,
                category_id=post.category_id,
                title=post.title,
                content=post.content,
                view_count=post.view_count,
                like_count=post.like_count,
                comment_count=post.comment_count,
                created_at=post.created_at,
                updated_at=post.updated_at,
                author_nickname=post.user.nickname if post.user else None,
                category_name=post.category.category_name if post.category else None,
                is_liked=is_liked
            ),
            "comments": comments_data
        }
    }


# 게시글 수정
@router.put("/posts/{post_id}", response_model=CommunityPostResponse)
async def update_post(post_id: int, user_id: int = Form(...), title: Optional[str] = Form(None), content: Optional[str] = Form(None), db: AsyncSession = Depends(get_db)):

    # 게시글 존재 확인
    post = await CommunityCRUD.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 작성자 확인
    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # 수정
    updated_post = await CommunityCRUD.update_post(db, post_id, title, content)
    
    # 최신 데이터 조회
    post_detail = await CommunityCRUD.get_post_by_id(db, post_id)
    
    return CommunityPostResponse(
        post_id=post_detail.post_id,
        user_id=post_detail.user_id,
        category_id=post_detail.category_id,
        title=post_detail.title,
        content=post_detail.content,
        view_count=post_detail.view_count,
        like_count=post_detail.like_count,
        comment_count=post_detail.comment_count,
        created_at=post_detail.created_at,
        updated_at=post_detail.updated_at,
        author_nickname=post_detail.user.nickname if post_detail.user else None,
        category_name=post_detail.category.category_name if post_detail.category else None
    )


# 게시글 삭제
@router.delete("/posts/{post_id}", response_model=dict)
async def delete_post(post_id: int, user_id: int = Query(...), db: AsyncSession = Depends(get_db)):

    # 게시글 존재 확인
    post = await CommunityCRUD.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # 작성자 확인
    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    # 삭제
    success = await CommunityCRUD.delete_post(db, post_id)
    
    return {"success": success, "message": "Post deleted successfully"}


# 특정 사용자의 게시글 목록 조회
@router.get("/posts/user/{user_id}", response_model=dict)
async def get_user_posts(user_id: int, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    skip = (page - 1) * page_size
    posts, total = await CommunityCRUD.get_user_posts(db, user_id, skip, page_size)
    
    posts_data = [
        CommunityPostListResponse(
            post_id=post.post_id,
            user_id=post.user_id,
            category_id=post.category_id,
            title=post.title,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            created_at=post.created_at,
            author_nickname=post.user.nickname if post.user else None,
            category_name=post.category.category_name if post.category else None
        )
        for post in posts
    ]
    
    return {
        "success": True,
        "data": posts_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


# 댓글과 대댓글 작성
@router.post("/posts/{post_id}/comments", response_model=CommunityCommentResponse)
async def create_comment(post_id: int, user_id: int = Form(...), content: str = Form(...), parent_comment_id: Optional[int] = Form(None), db: AsyncSession = Depends(get_db)):

    # 게시글 존재 확인
    post = await CommunityCRUD.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    comment = await CommunityCRUD.create_comment(db, post_id, user_id, content, parent_comment_id)
    
    return CommunityCommentResponse(
        comment_id=comment.comment_id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        parent_comment_id=comment.parent_comment_id,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


# 특정 게시글의 댓글 목록 조회
@router.get("/posts/{post_id}/comments", response_model=List[CommunityCommentResponse])
async def get_comments(post_id: int, db: AsyncSession = Depends(get_db)):

    comments = await CommunityCRUD.get_post_comments(db, post_id)
    
    return [
        CommunityCommentResponse(
            comment_id=comment.comment_id,
            post_id=comment.post_id,
            user_id=comment.user_id,
            parent_comment_id=comment.parent_comment_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            author_nickname=comment.user.nickname if comment.user else None,
            replies=[
                CommunityCommentResponse(
                    comment_id=reply.comment_id,
                    post_id=reply.post_id,
                    user_id=reply.user_id,
                    parent_comment_id=reply.parent_comment_id,
                    content=reply.content,
                    created_at=reply.created_at,
                    updated_at=reply.updated_at,
                    author_nickname=reply.user.nickname if reply.user else None
                )
                for reply in comment.replies
            ]
        )
        for comment in comments
    ]


# 댓글 수정
@router.put("/comments/{comment_id}", response_model=CommunityCommentResponse)
async def update_comment(comment_id: int, user_id: int = Form(...), content: str = Form(...), db: AsyncSession = Depends(get_db)):

    # 댓글 조회
    result = await db.execute(select(CommunityComment).filter(CommunityComment.comment_id == comment_id))
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 작성자 확인
    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    # 수정
    updated_comment = await CommunityCRUD.update_comment(db, comment_id, content)
    
    return CommunityCommentResponse(
        comment_id=updated_comment.comment_id,
        post_id=updated_comment.post_id,
        user_id=updated_comment.user_id,
        parent_comment_id=updated_comment.parent_comment_id,
        content=updated_comment.content,
        created_at=updated_comment.created_at,
        updated_at=updated_comment.updated_at
    )


# 댓글 삭제
@router.delete("/comments/{comment_id}", response_model=dict)
async def delete_comment(comment_id: int, user_id: int = Query(...), db: AsyncSession = Depends(get_db)):

    # 댓글 조회
    result = await db.execute(select(CommunityComment).filter(CommunityComment.comment_id == comment_id))
    comment = result.scalar_one_or_none()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # 작성자 확인
    if comment.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    # 삭제
    success = await CommunityCRUD.delete_comment(db, comment_id)
    
    return {"success": success, "message": "Comment deleted successfully"}


# 좋아요 토글 (누르기/취소)
@router.post("/posts/{post_id}/like", response_model=dict)
async def toggle_like(post_id: int, user_id: int = Form(...), db: AsyncSession = Depends(get_db)):

    # 게시글 존재 확인
    post = await CommunityCRUD.get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    result = await CommunityCRUD.toggle_like(db, post_id, user_id)
    
    # 현재 좋아요 수 조회
    updated_post = await CommunityCRUD.get_post_by_id(db, post_id)
    
    return {
        "success": True,
        "action": result["action"],
        "like_count": updated_post.like_count
    }


# 내가 좋아요한 게시글 목록
@router.get("/posts/liked", response_model=dict)
async def get_liked_posts(user_id: int = Query(...), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):

    skip = (page - 1) * page_size
    posts, total = await CommunityCRUD.get_user_liked_posts(db, user_id, skip, page_size)
    
    posts_data = [
        CommunityPostListResponse(
            post_id=post.post_id,
            user_id=post.user_id,
            category_id=post.category_id,
            title=post.title,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            created_at=post.created_at,
            author_nickname=post.user.nickname if post.user else None,
            category_name=post.category.category_name if post.category else None
        )
        for post in posts
    ]
    
    return {
        "success": True,
        "data": posts_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }

# delete category
@router.delete("/categories/{category_id}", status_code=200)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await CommunityCRUD.delete_category(db, category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}
