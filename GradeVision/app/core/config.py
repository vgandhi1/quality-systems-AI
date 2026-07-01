import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "GradeVision"
    PROJECT_VERSION: str = "0.1.0"

    DATABASE_URL: str = "sqlite:///./gradevisio n.db"
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars-long!"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    YOLOV5_MODEL_PATH: str = "yolov5/best.pt"
    CONFIDENCE_THRESHOLD: float = 0.5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
