from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, UploadFile
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token
from datetime import datetime
from app.database.crud.user import UserCrud as user_crud
from app.database.schemas.user import UserUpdate, UserReadWithProfile
from .email_service import email_service
from .image_service import ImageService
from ..database.crud.user import UserCrud
from app.database.models import Image, User


class UserService:
    # 회원가입
    @staticmethod
    async def register_user(db: AsyncSession, username: str, email: str, nickname: str, phone_number: str, password: str):
        # 중복 이메일 체크
        existing_email = await user_crud.get_user_by_email(db, email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다")

        # 중복 닉네임 체크
        existing_nickname = await user_crud.get_user_by_nickname(db, nickname)
        if existing_nickname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 닉네임입니다")

        hashed_pw = hash_password(password)
        return await user_crud.create_user(db, username, email, nickname, phone_number, hashed_pw)

    # 로그인
    @staticmethod
    async def login_user(db: AsyncSession, email: str, password: str) -> dict | None:
        user = await user_crud.get_user_by_email(db, email)

        if not user or not verify_password(password, user.password):
            return None

        access_token = create_access_token(data={"sub": str(user.user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user.user_id)})

        # 리프레시 토큰 DB 저장
        await user_crud.update_refresh_token(db, user.user_id, refresh_token)

        return {"access_token": access_token, "refresh_token": refresh_token}


    #유저 정보 조회(개인)
    @staticmethod
    async def get_user(db: AsyncSession, email:str):
        user = await user_crud.get_user_by_email(db,email)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자가 존재하지 않습니다")

        return user


    #모든 유저 정보 조회
    @staticmethod
    async def read_all_user(db: AsyncSession):
        users = await user_crud.get_all_user(db)
        return users

    #유저 삭제
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int):
        is_deleted = await user_crud.delete_user(db, user_id)

        if not is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{user_id} 사용자가 존재하지 않습니다")

        return {"message": "사용자 삭제 완료"}

    # 유저 업데이트
    @staticmethod
    async def update_user(db: AsyncSession, user_id: int ,user_data:UserUpdate):
        # 현재 유저 정보 조회
        current_user = await user_crud.get_user_by_id(db, user_id)
        if not current_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{user_id} 사용자가 존재하지 않습니다")

        # 이메일 변경 시 중복 체크 (본인 제외)
        if user_data.email and user_data.email != current_user.email:
            existing_email = await user_crud.get_user_by_email(db, user_data.email)
            if existing_email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다")

        # 닉네임 변경 시 중복 체크 (본인 제외)
        if user_data.nickname and user_data.nickname != current_user.nickname:
            existing_nickname = await user_crud.get_user_by_nickname(db, user_data.nickname)
            if existing_nickname:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="이미 사용 중인 닉네임입니다")

        hashed_password = None
        if user_data.password:
            hashed_password = hash_password(user_data.password)

        updated_user = await user_crud.update_user(
            db,
            user_id=user_id,
            user_name=user_data.username,
            email=user_data.email,
            nickname=user_data.nickname,
            phone_number=user_data.phone_number,
            hashed_password=hashed_password
        )

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{user_id} 사용자가 존재하지 않습니다")

        return updated_user

    # 리프레시 토큰으로 액세스 토큰 재발급
    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict | None:
        from app.core.jwt import verify_access_token
        try:
            payload = verify_access_token(refresh_token)
            user_id = int(payload.get("sub"))
            user = await user_crud.get_user_by_id(db, user_id)

            # DB에 저장된 리프레시 토큰과 비교
            if not user or user.refresh_token != refresh_token:
                return None

            # 새 액세스 토큰 발급
            new_access_token = create_access_token(data={"sub": str(user.user_id)})
            return {"access_token": new_access_token}

        except:
            return None


    # 비밀번호 찾기 (인증코드 발송)
    @staticmethod
    async def forgot_password(db: AsyncSession, email: str, username: str, phone_number: str):
        # 사용자 확인
        user = await UserCrud.get_user_by_credentials(db, email, username, phone_number)

        if not user: # 없으면 exception 발생
            raise HTTPException(status_code=404, detail="User Not Found")

        # 6자리 인증코드 생성
        reset_code = UserCrud.generate_reset_code()

        # DB에 코드 저장 (토큰의 유효기간은 15분)
        await UserCrud.save_reset_code(db, user.user_id, reset_code, expires_minutes=15)
        await db.commit()

        # 이메일 발송
        success, message = await email_service.send_reset_code_email(recipient_email=user.email, username=user.username, reset_code=reset_code)

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return {"message": "인증코드가 이메일로 발송되었습니다.", "expires_in_minutes": 15}

    # 인증코드로 비밀번호 재설정
    @staticmethod
    async def reset_password_with_code(db: AsyncSession, email: str, reset_code: str, new_password: str):
        # 인증코드 검증
        user = await UserCrud.verify_reset_code(db, email, reset_code)

        if not user:
            raise HTTPException(status_code=400, detail="인증코드가 유효하지 않거나 만료되었습니다.")

        try:
            # 비밀번호 해시화 및 비밀번호 변경
            hashed_password = hash_password(new_password)
            await UserCrud.update_user(db, user.user_id, hashed_password=hashed_password)

            # 인증코드 초기화(null로 변경)
            await UserCrud.clear_reset_code(db, user.user_id)

            await db.commit()

            return {"message": "비밀번호가 성공적으로 변경되었습니다."}

        except Exception as e:
            await db.rollback()
            print(f"비밀번호 재설정 오류: {str(e)}")  # 디버깅용
            raise HTTPException(status_code=500, detail="비밀번호 변경 중 오류가 발생했습니다.")


    @staticmethod
    async def update_profile_image(file: UploadFile, db: AsyncSession, user_id: int):
        result = await db.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 기존 프로필 이미지 삭제
        if user.profile_image_id:
            old_image_result = await db.execute(select(Image).filter(Image.id == user.profile_image_id))
            old_image = old_image_result.scalar_one_or_none()

            if old_image:
                await db.delete(old_image)

        # 새 이미지 업로드
        db_image = await ImageService.image_upload(file, db)

        # 유저에 이미지 연결
        user.profile_image_id = db_image.id
        await db.commit()
        await db.refresh(user)

        return user

    @staticmethod
    async def get_user_with_profile(db: AsyncSession, user_id: int) -> UserReadWithProfile:
        result = await db.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # UserReadWithProfile로 변환
        return UserReadWithProfile.from_user(user)

    @staticmethod
    async def delete_profile_image(db: AsyncSession, user_id: int):
        result = await db.execute(select(User).filter(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if not user.profile_image_id:
            raise HTTPException(status_code=404, detail="No profile image found")

        # 이미지 삭제
        image_result = await db.execute(select(Image).filter(Image.id == user.profile_image_id))
        image = image_result.scalar_one_or_none()

        if image:
            await db.delete(image)

        user.profile_image_id = None

        await db.commit()
        await db.refresh(user)

        return user