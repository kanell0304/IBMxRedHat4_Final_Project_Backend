from __future__ import annotations
from pathlib import Path
from datetime import timedelta
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILES = [BASE_DIR / ".env", BASE_DIR / "backend" / ".env"]

class Settings(BaseSettings):
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    db_host: str = Field("localhost", alias="DB_HOST")
    db_port: str = Field("3306", alias="DB_PORT")
    db_name: str = Field(..., alias="DB_NAME")

    secret_key: str = Field(..., alias="SECRET_KEY")
    jwt_algo: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_sec: int = Field(900, alias="ACCESS_TOKEN_EXPIRE")
    refresh_token_expire_sec: int = Field(604800, alias="REFRESH_TOKEN_EXPIRE")

    model_config = SettingsConfigDict(
        env_file=[str(p) for p in ENV_FILES],
        env_file_encoding="utf-8",
        extra="allow",
        populate_by_name=True,
        case_sensitive=True,
    )

    @property
    def tmp_db(self) -> str:
        return f"{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url(self) -> str:
        # Async SQLAlchemy(MySQL)
        return f"mysql+asyncmy://{self.tmp_db}"

    @property
    def sync_database_url(self) -> str:
        # Sync SQLAlchemy(MySQL)
        return f"mysql+pymysql://{self.tmp_db}"

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(seconds=self.access_token_expire_sec)

    @property
    def refresh_token_expire(self) -> timedelta:
        return timedelta(seconds=self.refresh_token_expire_sec)


settings = Settings()
