import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.crud import user as user_crud
from app.core.jwt import create_access_token, create_refresh_token
import os
from dotenv import load_dotenv

load_dotenv()

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

KAKAO_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


async def get_kakao_token(code: str) -> dict:
    """카카오 인가 코드로 액세스 토큰 발급"""
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_CLIENT_ID,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code,
        }
        
        if KAKAO_CLIENT_SECRET:
            data["client_secret"] = KAKAO_CLIENT_SECRET
        
        response = await client.post(
            KAKAO_TOKEN_URL,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"카카오 토큰 발급 실패: {response.text}"
            )
        
        return response.json()


async def get_kakao_user_info(access_token: str) -> dict:
    """카카오 액세스 토큰으로 사용자 정보 조회"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            KAKAO_USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"카카오 사용자 정보 조회 실패: {response.text}"
            )
        
        return response.json()


async def kakao_login_or_signup(db: AsyncSession, code: str) -> dict:
    """카카오 로그인 또는 회원가입 처리"""
    # 1. 인가 코드로 액세스 토큰 받기
    token_data = await get_kakao_token(code)
    kakao_access_token = token_data.get("access_token")
    
    # 2. 액세스 토큰으로 사용자 정보 받기
    user_info = await get_kakao_user_info(kakao_access_token)
    
    kakao_id = str(user_info.get("id"))
    kakao_account = user_info.get("kakao_account", {})
    email = kakao_account.get("email")
    profile = kakao_account.get("profile", {})
    nickname = profile.get("nickname", f"kakao_user_{kakao_id}")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="카카오 계정에서 이메일 정보를 가져올 수 없습니다"
        )
    
    # 3. DB에서 소셜 ID로 사용자 조회
    user = await user_crud.get_user_by_social_id(db, "kakao", kakao_id)
    
    is_new_user = False
    
    # 4. 없으면 회원가입, 있으면 로그인
    if not user:
        is_new_user = True
        # 이메일 중복 체크 (일반 회원가입과 충돌 방지)
        existing_user = await user_crud.get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 일반 회원가입으로 등록된 이메일입니다"
            )
        
        # 카카오 회원가입
        user = await user_crud.create_social_user(
            db=db,
            email=email,
            username=nickname,
            nickname=nickname,
            social_provider="kakao",
            social_id=kakao_id
        )
    
    # 5. JWT 토큰 발급
    access_token = create_access_token(data={"sub": str(user.user_id)})
    refresh_token = create_refresh_token(data={"sub": str(user.user_id)})
    
    # 6. 리프레시 토큰 DB 저장
    await user_crud.update_refresh_token(db, user.user_id, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "is_new_user": is_new_user
    }
