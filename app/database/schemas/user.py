from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional

# 사용자 관련 스키마
class UserBase(BaseModel):
    username: str
    email: EmailStr
    nickname: str

class UserCreate(UserBase):
    password: str
    phone_number: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    phone_number: Optional[str] = None
    profile_image: Optional[int] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        orm_mode = True

# kakao에서 필요한 필드 추가
class KakaoCallbackRequest(BaseModel):
    code: str

class KakaoLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    is_new_user: bool

# 비밀번호 찾기 요청 - 이메일, 이름, 전화번호 입력
class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    username: str
    phone_number: str

# 인증코드로 비밀번호 재설정
class ResetPasswordWithCode(BaseModel):
    email: EmailStr
    reset_code: str = Field(..., min_length=6, max_length=6)
    new_password: str

class UserReadWithProfile(UserResponse):
    profile_image_url: Optional[str] = None

    @classmethod
    def from_user(cls, user, base_url: str = ""):
        profile_url = None
        if user.profile_image_id:
            profile_url = f"{base_url}/image/raw/{user.profile_image_id}"

        return cls(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            nickname=user.nickname,
            phone_number=user.phone_number,
            created_at=user.created_at,
            profile_image=user.profile_image,
            profile_image_url=profile_url
        )
        
