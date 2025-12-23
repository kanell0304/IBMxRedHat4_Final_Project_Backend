from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.database.models.user import User
from app.database.models.roles import Roles, RoleEnum
from app.database.models.user_roles import UserRoles
from typing import Optional, List
from datetime import datetime, timedelta
import random
import string
import re

class UserCrud:

    # 유저 생성 (일반 회원가입)
    @staticmethod
    async def create_user(db: AsyncSession, username: str, email: str, nickname: str, phone_number: str, hashed_password: str) -> User:
        user = User(username=username,  email=email,  nickname=nickname,  phone_number=phone_number,  password=hashed_password)

        db.add(user)
        await db.flush()  # user.user_id를 얻기 위해 flush
        
        # USER role 조회
        result = await db.execute(select(Roles).where(Roles.role_name == RoleEnum.USER))
        user_role = result.scalar_one_or_none()
        
        if user_role:
            # user_roles 테이블에 직접 삽입
            user_role_association = UserRoles(user_id=user.user_id, role_id=user_role.id)
            db.add(user_role_association)
        
        await db.commit()
        
        # roles를 포함하여 다시 조회
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.user_id == user.user_id))
        user = result.scalar_one()

        return user


    # 이메일로 유저 조회 (roles 포함)
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.email == email))

        return result.scalar_one_or_none()


    # 닉네임으로 유저 조회
    @staticmethod
    async def get_user_by_nickname(db: AsyncSession, nickname: str) -> User | None:
        result = await db.execute(select(User).where(User.nickname == nickname))

        return result.scalar_one_or_none()


    # 유저네임으로 유저 조회
    @staticmethod
    async def get_user_by_username(db: AsyncSession, user_name: str) -> User | None:
        result = await db.execute(select(User).where(User.username == user_name))

        return result.scalar_one_or_none()


    # 아이디로 유저 조회 (roles 포함)
    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.user_id == user_id))

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
        result = await db.execute(
            select(User).options(selectinload(User.roles))
        )

        return result.scalars().all()


    # 소셜 ID로 유저 조회
    @staticmethod
    async def get_user_by_social_id(db: AsyncSession, provider: str, social_id: str) -> User | None:

        result = await db.execute(select(User).where(User.social_provider == provider, User.social_id == social_id))

        return result.scalar_one_or_none()


    # 소셜 유저 생성 (카카오 회원가입)
    @staticmethod
    async def create_social_user(db: AsyncSession, email: str, username: str, nickname: str, social_provider: str, social_id: str) -> User:

        # kakao api로 받아온 값들로 회원가입 로직 수행(단, 소셜 회원가입이기때문에 is_social=1)
        user = User(
            email=email,
            username=username,
            nickname=nickname,
            is_social=1,
            social_provider=social_provider,
            social_id=social_id,
            password=None,
            phone_number=None
        )

        db.add(user)
        await db.flush()  # user.user_id를 얻기 위해 flush
        
        # user_roles 조회
        result = await db.execute(select(Roles).where(Roles.role_name == RoleEnum.USER))
        user_role = result.scalar_one_or_none()
        
        if user_role:
            # user_roles 테이블에 직접 삽입
            user_role_association = UserRoles(user_id=user.user_id, role_id=user_role.id)
            db.add(user_role_association)
        
        await db.commit()
        
        # roles를 포함하여 다시 조회
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.user_id == user.user_id))
        user = result.scalar_one()

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

        result = await db.execute(select(User).where(User.email == email, User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            return None

        def normalize(number: str) -> str:
            return re.sub(r'\D', '', number or '')

        # 전화번호 비교 시 하이픈/공백 등 포맷을 제거해 일치 여부를 판단
        if normalize(user.phone_number) == normalize(phone_number):
            return user

        return None


    # 6자리 인증코드 생성
    @staticmethod
    def generate_reset_code() -> str:

        return ''.join(random.choices(string.digits, k=6))


    # 인증코드 저장 (User 모델에 필드 추가한 경우)
    @staticmethod
    async def save_reset_code(db: AsyncSession, user_id: int, code: str, expires_minutes: int = 15):

        user = await db.get(User, user_id)

        if user:
            user.reset_code = code
            user.reset_code_expires_at = datetime.now() + timedelta(minutes=expires_minutes)
            await db.flush()

        return user


    # 인증코드 검증(유효 기간이 지났는지)
    @staticmethod
    async def verify_reset_code(db: AsyncSession, email: str, code: str) -> Optional[User]:

        result = await db.execute(select(User).where(User.email == email, User.reset_code == code, User.reset_code_expires_at > datetime.now()))

        return result.scalar_one_or_none()


    # 인증코드 초기화 - 작업이 완료되면 임시로 부여한 인증 코드 값 초기화 => null
    @staticmethod
    async def clear_reset_code(db: AsyncSession, user_id: int):

        user = await db.get(User, user_id)

        if user:
            user.reset_code = None
            user.reset_code_expires_at = None
            await db.flush()

        return user
