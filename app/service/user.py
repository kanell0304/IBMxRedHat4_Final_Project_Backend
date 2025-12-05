from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token
from datetime import datetime
from app.database.crud import user as user_crud
from app.database.schemas.user import UserUpdate

# 회원가입
async def register_user(db: AsyncSession, username: str, email: str, nickname: str, phone_number: str, password: str):
    # 중복 이메일 체크
    existing_email = await user_crud.get_user_by_email(db, email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다"
        )

    hashed_pw = hash_password(password)
    return await user_crud.create_user(db, username, email, nickname, phone_number, hashed_pw)

# 로그인
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
async def get_user(db: AsyncSession, email:str):
    user = await user_crud.get_user_by_email(db,email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자가 존재하지 않습니다"
        )
    
    return user


#모든 유저 정보 조회
async def read_all_user(db: AsyncSession):
    users = await user_crud.get_all_user(db)
    return users

#유저 삭제 
async def delete_user(db: AsyncSession, user_id: int):
    is_deleted = await user_crud.delete_user(db, user_id)
    if not is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{user_id} 사용자가 존재하지 않습니다"
        )
    return {"message": "사용자 삭제 완료"}

# 유저 업데이트
async def update_user(db: AsyncSession, user_id: int ,user_data:UserUpdate):
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{user_id} 사용자가 존재하지 않습니다"
        )

    return updated_user

# 리프레시 토큰으로 액세스 토큰 재발급
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