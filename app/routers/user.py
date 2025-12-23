import os
from dotenv import load_dotenv
from app.service.kakao_oauth import kakao_login_or_signup
load_dotenv()
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from fastapi import UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.schemas.user import UserCreate, UserResponse, UserLogin, UserUpdate, Token, UserBase, KakaoLoginResponse, KakaoCallbackRequest, ForgotPasswordRequest, ResetPasswordWithCode, UserReadWithProfile
from ..service.user import UserService
from app.database.models.user import User as UserModel
from typing import List, Optional
from jose import JWTError
from app.core.jwt import verify_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ..database.crud.user import UserCrud


router = APIRouter(prefix='/users',tags=['User'])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


# 쿠키에서 토큰 가져오기
async def get_token_from_cookie(access_token: Optional[str] = Cookie(None)) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증 토큰이 없습니다", headers={"WWW-Authenticate": "Bearer"})

    return access_token


async def get_current_user(db: AsyncSession = Depends(get_db), token: str = Depends(get_token_from_cookie)) -> UserModel:
    try:
        payload = verify_access_token(token)
        user_id_str: str = payload.get("sub")

        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="존재하지 않는 사용자 ID입니다",)

        user_id = int(user_id_str)

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials (JWT오류)", headers={"WWW-Authenticate": "Bearer"})
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials", headers={"WWW-Authenticate": "Bearer"})

    user = await UserCrud.get_user_by_id(db, user_id)
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="삭제된 사용자 ID입니다",headers={"WWW-Authenticate": "Bearer"})
    
    return user


@router.post("/login")
async def login_for_user(response: Response, user: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    email = user.username
    result = await UserService.login_user(db, email, user.password)

    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})

    # 쿠키에 토큰 저장
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=1500 * 60,
    )
    
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
    )

    return {
        "message": "로그인 성공",
        "token_type": "bearer",
        "user": result["user"]
    }


# 로그아웃 (쿠키 삭제)
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "로그아웃 성공"}


# 유저 생성
@router.post("/join", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    new_user = await UserService.register_user(db, user.username, user.email, user.nickname, user.phone_number, user.password)

    return new_user


# 사용자 조회 - 프로필 이미지 URL 포함
@router.get("/me", response_model=UserReadWithProfile)
async def get_authenticated_user(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await UserService.get_user_with_profile(db, current_user.user_id)


@router.get("/", response_model=List[UserResponse])
async def read_all_user_route(db: AsyncSession = Depends(get_db)):
    users = await UserService.read_all_user(db)

    return users


# 유저 삭제
@router.delete("/me", status_code=status.HTTP_200_OK)
async def del_user(db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    msg = await UserService.delete_user(db, current_user.user_id)

    return msg


# 유저 업데이트
@router.patch("/me", response_model=UserResponse)
async def upd_user(user_data: UserUpdate, db: AsyncSession = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    mod_user = await UserService.update_user(db, current_user.user_id, user_data)

    return mod_user


# 리프레시 토큰으로 액세스 토큰 재발급
@router.post("/refresh")
async def refresh_token(response: Response,  refresh_token: Optional[str] = Cookie(None),  db: AsyncSession = Depends(get_db)):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  detail="Refresh token이 없습니다")
    
    new_tokens = await UserService.refresh_access_token(db, refresh_token)

    if not new_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,  detail="Invalid refresh token")
    
    # 새 액세스 토큰을 쿠키에 저장
    response.set_cookie(
        key="access_token",
        value=new_tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=1500 * 60,
    )
    
    return {"message": "토큰 갱신 성공"}


# 카카오 로그인 URL 생성
@router.get("/kakao/login-url")
async def get_kakao_login_url():
    # 기본 URL
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={os.getenv('KAKAO_CLIENT_ID')}"
        f"&redirect_uri={os.getenv('KAKAO_REDIRECT_URI')}"
        f"&response_type=code"
    )
    
    # 개발 환경에서만 prompt=login 추가 (테스트용)
    environment = os.getenv('ENVIRONMENT', 'production')
    if environment == 'development':
        kakao_auth_url += "&prompt=login"
    
    return {"auth_url": kakao_auth_url}


# 카카오 인가 코드로 로그인/회원가입 처리
@router.post("/kakao/callback")
async def kakao_login(request: KakaoCallbackRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await kakao_login_or_signup(db, request.code)

    # 쿠키에 토큰 저장
    response.set_cookie(
        key="access_token",
        value=result["access_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=1500 * 60,
    )
    
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=604800,
    )

    return {
        "message": "로그인 성공",
        "is_new_user": result.get("is_new_user", False),
        "token_type": "bearer",
        "user": result["user"]
    }


# 비밀번호 찾기 (인증코드 발송)
@router.post("/forgot-password", summary="비밀번호 찾기 (인증코드 발송)")
async def forgot_password(request: ForgotPasswordRequest,  db: AsyncSession = Depends(get_db)):
    return await UserService.forgot_password(db, request.email, request.username, request.phone_number)


# 인증코드로 비밀번호 재설정
@router.post("/reset-password", summary="비밀번호 재설정 (인증코드)")
async def reset_password_with_code(request: ResetPasswordWithCode,  db: AsyncSession = Depends(get_db)):
    return await UserService.reset_password_with_code(db, request.email, request.reset_code, request.new_password)


# 프로필 이미지 업로드/변경
@router.post("/me/profile-image", response_model=UserReadWithProfile)
async def upload_profile_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    user = await UserService.update_profile_image(file, db, current_user.user_id)
    return UserReadWithProfile.from_user(user, base_url="")


# 프로필 이미지 삭제
@router.delete("/me/profile-image", response_model=UserReadWithProfile)
async def delete_profile_image(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    user = await UserService.delete_profile_image(db, current_user.user_id)
    return UserReadWithProfile.from_user(user, base_url="")

# 유저 삭제 (관리용)
@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def del_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    msg = await UserService.delete_user(db, user_id)
    return msg