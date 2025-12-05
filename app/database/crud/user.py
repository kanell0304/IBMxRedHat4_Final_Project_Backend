from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models.user import User
from typing import Optional, List


# 유저 생성
async def create_user(db: AsyncSession, username: str, email: str, nickname: str, phone_number: str,hashed_password: str) -> User:
    user = User(username=username, email=email, nickname=nickname, phone_number=phone_number, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# 이메일로 유저 조회
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


# 유저네임으로 유저 조회
async def get_user_by_username(db: AsyncSession, user_name: str) -> User | None:
    result = await db.execute(select(User).where(User.username == user_name))
    return result.scalar_one_or_none()


# 아이디로 유저 조회
async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


# 유저 업데이트
async def update_user(db: AsyncSession,
                      user_id: int,
                      user_name: Optional[str] = None,
                      email: Optional[str] = None,
                      nickname: Optional[str] = None,
                      phone_number: Optional[str] = None,
                      hashed_password: Optional[str] = None) -> Optional[User]:
    # 유저ID로 유저 조회
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return None
    if user_name is not None:
        user.username = user_name
    if email is not None:
        user.email = email
    if nickname is not None:
        user.nickname = nickname
    if phone_number is not None:
        user.phone_number = phone_number
    if hashed_password is not None:
        user.password = hashed_password

    await db.commit()
    await db.refresh(user)

    return user


# 리프레시 토큰 업데이트
async def update_refresh_token(db: AsyncSession, user_id: int, refresh_token: str) -> bool:
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    user.refresh_token = refresh_token
    await db.commit()
    await db.refresh(user)

    return True


# 유저 삭제
async def delete_user(db: AsyncSession, user_id: str) -> bool:
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    await db.delete(user)
    await db.commit()
    return True


# 모든 유저 조회
async def get_all_user(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))

    return result.scalars().all()


# 소셜 ID로 유저 조회
async def get_user_by_social_id(db: AsyncSession, provider: str, social_id: str) -> User | None:
    result = await db.execute(select(User).where(User.social_provider == provider, User.social_id == social_id))

    return result.scalar_one_or_none()


# 소셜 유저 생성
async def create_social_user(db: AsyncSession, email: str, username: str, nickname: str, social_provider: str, social_id: str) -> User:

    # kakao api로 받아온 값들로 회원가입 로직 수행(단, 소셜 회원가입이기때문에 is_social=1)
    user = User( # 유저 객체 생성
        email=email,
        username=username,
        nickname=nickname,
        is_social=1,
        social_provider=social_provider,
        social_id=social_id,
        password=None, # 어차피 kakao 계정으로 로그인 할 거기 때문에 필요 x
        phone_number=None # kakao로 로그인 하기때문에 필요 x -> 폰번호는 어차피 비밀번호 찾기에 사용할 예정
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user
