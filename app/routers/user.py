import os
from dotenv import load_dotenv
from app.service.kakao_oauth import kakao_login_or_signup
load_dotenv()
from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate, Token, UserBase, \
    KakaoLoginResponse, KakaoCallbackRequest
from app.service.user import register_user,login_user,delete_user,get_user, update_user, read_all_user, refresh_access_token
from app.database.models.user import User as UserModel
from typing import Annotated , List
from jose import JWTError
from app.core.jwt import verify_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.database.crud import user as user_crud


router = APIRouter(prefix='/users',tags=['User'])

DB_Dependency = Annotated[AsyncSession, Depends(get_db)]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


async def get_current_user(db: DB_Dependency, token: str = Depends(oauth2_scheme)) -> UserModel:
    try:
        payload = verify_access_token(token)
        user_id_str: str = payload.get("sub") # 토큰에서 사용자 ID(sub) 추출
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="존재하지 않는 사용자 ID입니다",
            )
        user_id = int(user_id_str)

    except JWTError:
        # 토큰 디코딩 실패 (만료되었거나 서명이 유효하지 않음)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials (JWT오류)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        # verify_access_token에서 발생한 기타 예외 처리
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_crud.get_user_by_id(db, user_id)
    
    if user is None:
        # 토큰은 유효하지만 DB에 해당 유저가 없는 경우 (삭제된 계정)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="삭제된 사용자 ID입니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


Auth_Dependency = Annotated[UserModel, Depends(get_current_user)]


@router.post("/login", response_model=Token)
async def login_for_user(user:OAuth2PasswordRequestForm=Depends(), db:AsyncSession=Depends(get_db)):
    email = user.username
    tokens = await login_user(db, email, user.password)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": "bearer"
    }

# 유저 생성
@router.post("/join", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    new_user = await register_user(db, user.username, user.email, user.nickname, user.phone_number, user.password)
    return new_user


# 사용자 조회
@router.get("/me", response_model=UserResponse)
async def get_authenticated_user(current_user: Auth_Dependency):
    return current_user

@router.get("/", response_model=List[UserResponse])
async def read_all_user_route(db: DB_Dependency, current_user: Auth_Dependency):
    users = await read_all_user(db)
    return users

# 유저 삭제
@router.delete("/me",status_code=status.HTTP_200_OK)
async def del_user(db : DB_Dependency, current_user: Auth_Dependency):
    msg = await delete_user(db, current_user.user_id)
    return msg

# 유저 업데이트
@router.patch("/me" , response_model=UserResponse)
async def upd_user(
        user_data: UserUpdate,
        db: DB_Dependency,
        current_user: Auth_Dependency
    ):
    mod_user = await update_user(
        db,
        current_user.user_id,
        user_data
    )
    return mod_user

# 리프레시 토큰으로 액세스 토큰 재발급
@router.post("/refresh")
async def refresh_token(refresh_token: str, db: DB_Dependency):
    new_tokens = await refresh_access_token(db, refresh_token)
    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    return new_tokens


# 카카오 로그인 URL 생성 (프론트엔드에서 필요시 호출)
@router.get("/kakao/login-url")
async def get_kakao_login_url():
    """프론트엔드에서 카카오 로그인 URL을 받기 위한 엔드포인트"""
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={os.getenv('KAKAO_CLIENT_ID')}"
        f"&redirect_uri={os.getenv('KAKAO_REDIRECT_URI')}"
        f"&response_type=code"
    )
    return {"auth_url": kakao_auth_url}


# 카카오 인가 코드로 로그인/회원가입 처리
@router.post("/kakao/callback", response_model=KakaoLoginResponse)
async def kakao_login(request: KakaoCallbackRequest, db: DB_Dependency):
    tokens = await kakao_login_or_signup(db, request.code)
    return tokens