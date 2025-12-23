from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from ..models.community import CommunityCategory, CommunityPost, CommunityComment, CommunityPostLike
from ..models.user import User


class CommunityCRUD:

    # 카테고리 생성
    @staticmethod
    async def create_category(db: AsyncSession, category_name: str, description: Optional[str] = None) -> CommunityCategory:
        category = CommunityCategory(category_name=category_name, description=description)

        db.add(category)
        await db.commit()
        await db.refresh(category)

        return category

    # 모든 카테고리 조회
    @staticmethod
    async def get_all_categories(db: AsyncSession) -> List[CommunityCategory]:
        result = await db.execute(select(CommunityCategory).order_by(CommunityCategory.category_id))

        return result.scalars().all()

    # community_category_id로 조회
    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> Optional[CommunityCategory]:
        result = await db.execute(select(CommunityCategory).filter(CommunityCategory.category_id == category_id))

        return result.scalar_one_or_none()

    # 카테고리 삭제
    @staticmethod
    async def delete_category(db: AsyncSession, category_id: int) -> bool:
        result = await db.execute(
            delete(CommunityCategory).where(CommunityCategory.category_id == category_id)
        )
        await db.commit()
        return result.rowcount > 0

    # 게시글 생성
    @staticmethod
    async def create_post(db: AsyncSession, user_id: int, category_id: int, title: str, content: str) -> CommunityPost:
        post = CommunityPost(user_id=user_id, category_id=category_id, title=title, content=content)

        db.add(post)
        await db.commit()
        await db.refresh(post)

        return post

    # 게시글 상세 조회 (댓글, 작성자 정보 포함)
    @staticmethod
    async def get_post_by_id(db: AsyncSession, post_id: int, increment_view: bool = False) -> Optional[CommunityPost]:

        # 조회수 증가
        if increment_view:
            await db.execute(update(CommunityPost).where(CommunityPost.post_id == post_id).values(view_count=CommunityPost.view_count + 1))

            await db.commit()
        
        result = await db.execute(
            select(CommunityPost)
            .options(
                joinedload(CommunityPost.user),
                joinedload(CommunityPost.category),
                selectinload(CommunityPost.comments).selectinload(CommunityComment.user),
                selectinload(CommunityPost.comments).selectinload(CommunityComment.replies).selectinload(CommunityComment.user)
            )
            .filter(CommunityPost.post_id == post_id)
        )

        return result.unique().scalar_one_or_none()

    # 게시글 목록 조회 (페이징, 필터링, 정렬)
    @staticmethod
    async def get_posts(db: AsyncSession, category_id: Optional[int] = None, skip: int = 0, limit: int = 20, order_by: str = "latest") -> Tuple[List[CommunityPost], int]:

        query = select(CommunityPost).options(
            joinedload(CommunityPost.user),
            joinedload(CommunityPost.category)
        )
        
        # 카테고리 필터
        if category_id:
            query = query.filter(CommunityPost.category_id == category_id)
        
        # 정렬
        if order_by == "popular":
            query = query.order_by(CommunityPost.like_count.desc())
        elif order_by == "views":
            query = query.order_by(CommunityPost.view_count.desc())
        else:  # latest
            query = query.order_by(CommunityPost.created_at.desc())
        
        # 총 개수 조회
        count_query = select(func.count(CommunityPost.post_id))
        if category_id:
            count_query = count_query.filter(CommunityPost.category_id == category_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # 페이징 적용
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        posts = result.unique().scalars().all()
        
        return posts, total

    # 특정 사용자의 게시글 조회
    @staticmethod
    async def get_user_posts(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[CommunityPost], int]:
        # 총 개수
        count_result = await db.execute(select(func.count(CommunityPost.post_id)).filter(CommunityPost.user_id == user_id))
        total = count_result.scalar()
        
        # 게시글 조회
        result = await db.execute(
            select(CommunityPost)
            .options(
                joinedload(CommunityPost.user),
                joinedload(CommunityPost.category)
            )
            .filter(CommunityPost.user_id == user_id)
            .order_by(CommunityPost.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        posts = result.unique().scalars().all()
        
        return posts, total

    # 게시글 수정
    @staticmethod
    async def update_post(db: AsyncSession, post_id: int, title: Optional[str] = None, content: Optional[str] = None) -> Optional[CommunityPost]:
        result = await db.execute(select(CommunityPost).filter(CommunityPost.post_id == post_id))
        post = result.scalar_one_or_none()
        
        if not post:
            return None
        
        if title is not None:
            post.title = title
        if content is not None:
            post.content = content
        
        await db.commit()
        await db.refresh(post)

        return post

    # 게시글 삭제
    @staticmethod
    async def delete_post(db: AsyncSession, post_id: int) -> bool:

        result = await db.execute(delete(CommunityPost).where(CommunityPost.post_id == post_id))
        await db.commit()

        return result.rowcount > 0

    # 댓글과 대댓글 생성
    @staticmethod
    async def create_comment(db: AsyncSession, post_id: int, user_id: int, content: str, parent_comment_id: Optional[int] = None) -> CommunityComment:

        comment = CommunityComment(post_id=post_id, user_id=user_id, content=content, parent_comment_id=parent_comment_id)
        db.add(comment)
        
        # 게시글의 댓글 수 증가
        await db.execute(update(CommunityPost).where(CommunityPost.post_id == post_id).values(comment_count=CommunityPost.comment_count + 1))
        
        await db.commit()
        await db.refresh(comment)

        return comment

    # 게시글의 댓글 조회 (대댓글 포함, 부모 댓글만)
    @staticmethod
    async def get_post_comments(db: AsyncSession, post_id: int) -> List[CommunityComment]:
        result = await db.execute(
            select(CommunityComment)
            .options(
                joinedload(CommunityComment.user),
                selectinload(CommunityComment.replies).joinedload(CommunityComment.user)
            )
            .filter(
                CommunityComment.post_id == post_id,
                CommunityComment.parent_comment_id.is_(None)  # 부모 댓글만
            )
            .order_by(CommunityComment.created_at.asc())
        )
        return result.unique().scalars().all()

    # 댓글 수정
    @staticmethod
    async def update_comment(db: AsyncSession, comment_id: int, content: str) -> Optional[CommunityComment]:

        result = await db.execute(select(CommunityComment).filter(CommunityComment.comment_id == comment_id))
        comment = result.scalar_one_or_none()
        
        if not comment:
            return None
        
        comment.content = content

        await db.commit()
        await db.refresh(comment)

        return comment

    # 댓글 삭제
    @staticmethod
    async def delete_comment(db: AsyncSession, comment_id: int) -> bool:

        # 댓글 조회
        result = await db.execute(select(CommunityComment).filter(CommunityComment.comment_id == comment_id))
        comment = result.scalar_one_or_none()
        
        if not comment:
            return False
        
        post_id = comment.post_id
        
        # 댓글 삭제 (cascade설정으로 대댓글도 함께 삭제됨)
        await db.execute(delete(CommunityComment).where(CommunityComment.comment_id == comment_id))
        
        # 게시글의 댓글 수 감소 (대댓글 수 포함)
        deleted_count_result = await db.execute(
            select(func.count(CommunityComment.comment_id))
            .filter(
                (CommunityComment.comment_id == comment_id) |
                (CommunityComment.parent_comment_id == comment_id)
            )
        )
        deleted_count = deleted_count_result.scalar()
        
        await db.execute(update(CommunityPost).where(CommunityPost.post_id == post_id).values(comment_count=CommunityPost.comment_count - deleted_count))
        
        await db.commit()
        return True

    # 좋아요 토글 (누르기/취소) - user_id를 기준으로 조회해서 누른 기록이 있다면 취소
    @staticmethod
    async def toggle_like(db: AsyncSession, post_id: int, user_id: int) -> dict:

        # 이미 좋아요를 눌렀는지 확인
        result = await db.execute(
            select(CommunityPostLike)
            .filter(
                CommunityPostLike.post_id == post_id,
                CommunityPostLike.user_id == user_id
            )
        )
        existing_like = result.scalar_one_or_none()

        # 좋아요 취소 - 누른 기록이 있다면
        if existing_like:
            await db.execute(
                delete(CommunityPostLike)
                .where(
                    CommunityPostLike.post_id == post_id,
                    CommunityPostLike.user_id == user_id
                )
            )

            # 좋아요를 취소했으니 해당 게시글의 좋아요 수 감소
            await db.execute(update(CommunityPost).where(CommunityPost.post_id == post_id).values(like_count=CommunityPost.like_count - 1))
            await db.commit()

            return {"action": "unliked", "like_count": -1}
        else:
            # 좋아요 추가
            like = CommunityPostLike(post_id=post_id, user_id=user_id)
            db.add(like)
            # 게시글의 좋아요 수 증가
            await db.execute(update(CommunityPost).where(CommunityPost.post_id == post_id).values(like_count=CommunityPost.like_count + 1))
            await db.commit()

            return {"action": "liked", "like_count": 1}

    # 사용자가 게시글에 좋아요를 눌렀는지 확인
    @staticmethod
    async def check_user_liked(db: AsyncSession, post_id: int, user_id: int) -> bool:

        result = await db.execute(
            select(CommunityPostLike)
            .filter(
                CommunityPostLike.post_id == post_id,
                CommunityPostLike.user_id == user_id
            )
        )

        return result.scalar_one_or_none() is not None

    # 사용자가 좋아요한 게시글 목록 조회
    @staticmethod
    async def get_user_liked_posts(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 20) -> Tuple[List[CommunityPost], int]:

        # 총 개수
        count_result = await db.execute(select(func.count(CommunityPostLike.like_id)).filter(CommunityPostLike.user_id == user_id))
        total = count_result.scalar()
        
        # 게시글 조회
        result = await db.execute(
            select(CommunityPost)
            .join(CommunityPostLike, CommunityPost.post_id == CommunityPostLike.post_id)
            .options(
                joinedload(CommunityPost.user),
                joinedload(CommunityPost.category)
            )
            .filter(CommunityPostLike.user_id == user_id)
            .order_by(CommunityPostLike.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        posts = result.unique().scalars().all()
        
        return posts, total
