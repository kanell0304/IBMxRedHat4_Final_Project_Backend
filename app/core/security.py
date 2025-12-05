#비밀번호 암호화
from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    safe_password_string = password[:72]
    return pwd_context.hash(safe_password_string)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe_plain_password_string = plain_password[:72]
    return pwd_context.verify(safe_plain_password_string, hashed_password)