from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.core.settings import settings
from fastapi import HTTPException, status
from typing import Optional
from jose.exceptions import ExpiredSignatureError

# 액세스 토큰 생성
def create_access_token(data:dict, expires_time: Optional[int] = 1500):
  to_encode = data.copy()
  exp = datetime.utcnow() + timedelta(minutes=expires_time)
  to_encode["exp"] = exp
  return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algo)

# 리프레시 토큰 생성
def create_refresh_token(data:dict):
  to_encode = data.copy()
  exp = datetime.utcnow() + timedelta(seconds=settings.refresh_token_expire_sec)
  to_encode["exp"] = exp
  return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algo)

# 토큰 검증
def verify_access_token(token: str):
    try:
        return jwt.decode(token, settings.secret_key, algorithms=settings.jwt_algo)
    except (ExpiredSignatureError, JWTError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials (JWT오류)",
            headers={"WWW-Authenticate": "Bearer"},
        )