from __future__ import annotations
from pathlib import Path
from datetime import timedelta
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILES = BASE_DIR / ".env"

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

    #Google stt API
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(..., alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_cloud_project_id: str = Field(..., alias="GOOGLE_CLOUD_PROJECT_ID")

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="allow",
        populate_by_name=True,
        case_sensitive=True,
    )

    # LLM 설정 : openai or watsonx
    llm_provider:str=Field("", alias="LLM_PROVIDER")

    # OpenAI
    openai_api_key:str=Field("", alias="OPENAI_API_KEY")
    openai_model:str=Field("gpt-4o-mini", alias="OPENAI_MODEL")

    # IBM Watsonx
    watsonx_api_key:str=Field("", alias="WATSONX_API_KEY")
    watson_project_id:str=Field("", alias="WATSONX_PROJECT_ID")
    watsonx_url:str=Field("https://us-south.ml.cloud.ibm.com", alias="WATSONX_URL")
    watsonx_model:str=Field("meta-llama/llama-3-1-70b-instruct", alias="WATSONX_MODEL")


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
