from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.models.user import User
from typing import Optional, List
from datetime import datetime, timedelta
import random
import string

class UserCrud:

    # 유저 생성
    @staticmethod
    async def create_user(db: AsyncSession, username: str, email: str, nickname: str, phone_number: str,hashed_password: str) -> User:
        user = User(username=username, email=email, nickname=nickname, phone_number=phone_number, password=hashed_password)

        db.add(user)
        await db.commit()
        await db.refresh(user)

        return user


    # 이메일로 유저 조회
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))

        return result.scalar_one_or_none()


    # 유저네임으로 유저 조회
    @staticmethod
    async def get_user_by_username(db: AsyncSession, user_name: str) -> User | None:
        result = await db.execute(select(User).where(User.username == user_name))

        return result.scalar_one_or_none()


    # 아이디로 유저 조회
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).where(User.user_id == user_id))

        return result.scalar_one_or_none()


    # 유저 업데이트
    @staticmethod
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
    @staticmethod
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
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> bool:

        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user is None:
            return False

        await db.delete(user)
        await db.commit()
        return True


    # 모든 유저 조회
    @staticmethod
    async def get_all_user(db: AsyncSession) -> List[User]:

        result = await db.execute(select(User))

        return result.scalars().all()


    # 소셜 ID로 유저 조회
    @staticmethod
    async def get_user_by_social_id(db: AsyncSession, provider: str, social_id: str) -> User | None:

        result = await db.execute(select(User).where(User.social_provider == provider, User.social_id == social_id))

        return result.scalar_one_or_none()


    # 소셜 유저 생성
    @staticmethod
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

    # 해당 user 테이블의 refresh_token 재설정 - refresh_token 재발급
    @staticmethod
    async def update_refresh_token_id(db: AsyncSession, user_id: int, refresh_token: str) -> Optional[User]:
        db_user = await db.get(User, user_id)

        if db_user:
            db_user.refresh_token = refresh_token
            await db.flush()

        return db_user

    # 해당 user 테이블의 refresh_token 삭제 - 로그아웃
    @staticmethod
    async def delete_refresh_token(db: AsyncSession, refresh_token: str) -> Optional[User]:

        result = await db.execute(select(User).where(User.refresh_token == refresh_token))
        db_user = result.scalar_one_or_none()

        if db_user:
            db_user.refresh_token = None
            await db.flush()

        return db_user

    # 유저 목록 조회 - 일정 개수 제한
    @staticmethod
    async def list(db: AsyncSession, skip: int = 0, limit: int = 50) -> List[User]:

        result = await db.execute(select(User).offset(skip).limit(limit))

        return list(result.scalars().all())


    # 입력 받은 이메일, 이름, 전화번호가 모두 동일한 유저 조회
    @staticmethod
    async def get_user_by_credentials(db: AsyncSession, email: str, username: str, phone_number: str) -> Optional[User]:

        result = await db.execute(select(User).where(User.email == email, User.username == username, User.phone_number == phone_number)) # 이메일, 이름, 전화번호가 모두 일치하는 유저 조회

        return result.scalar_one_or_none()


    # 6자리 인증코드 생성
    @staticmethod
    def generate_reset_code() -> str:

        return ''.join(random.choices(string.digits, k=6))


    # 인증코드 저장 (User 모델에 필드 추가한 경우)
    @staticmethod
    async def save_reset_code(db: AsyncSession, user_id: int, code: str, expires_minutes: int = 15): # expires_minutes = 15 => 임시 인증 코드의 유효 기간이 15분 이다~

        user = await db.get(User, user_id) # user_id로 유저 조회 후

        if user: # 유저가 존재하면
            user.reset_code = code # 인증코드 저장
            user.reset_code_expires_at = datetime.now() + timedelta(minutes=expires_minutes) # 인증코드 유효 기간 저장
            await db.flush()

        return user


    # 인증코드 검증(유효 기간이 지났는지)
    @staticmethod
    async def verify_reset_code(db: AsyncSession, email: str, code: str) -> Optional[User]:

        result = await db.execute(select(User).where(User.email == email, User.reset_code == code, User.reset_code_expires_at > datetime.now()))  # 인증코드 만료 확인(15분이 지났는지)

        return result.scalar_one_or_none()


    # 인증코드 초기화 - 작업이 완료되면 임시로 부여한 인증 코드 값 초기화 => null
    @staticmethod
    async def clear_reset_code(db: AsyncSession, user_id: int):

        user = await db.get(User, user_id) # 해당 유저 정보를 조회

        if user:
            user.reset_code = None # null로 변경
            user.reset_code_expires_at = None # null로 변경
            await db.flush()

        return user
