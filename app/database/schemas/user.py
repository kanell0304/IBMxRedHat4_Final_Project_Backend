from pydantic import BaseModel, EmailStr
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
    user_id: int
    phone_number: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    class Config:
        orm_mode = True

class KakaoCallbackRequest(BaseModel):
    code: str

class KakaoLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    is_new_user: bool
        
