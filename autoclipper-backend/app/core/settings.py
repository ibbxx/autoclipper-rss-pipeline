from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    rq_queue_name: str = Field(default="default", alias="RQ_QUEUE_NAME")
    
    groq_api_key: str = Field(alias="GROQ_API_KEY")

    poll_interval_seconds: int = Field(default=600, alias="POLL_INTERVAL_SECONDS")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
