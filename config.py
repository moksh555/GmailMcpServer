from pydantic_settings import BaseSettings, SettingsConfigDict #type:ignore
from pathlib import Path
import os

CURRENT_FOLDER = Path(__file__).parent.absolute()
ENV_FILE_PATH = CURRENT_FOLDER / ".env"

class Settings(BaseSettings):
    
    GMAIL_TOKEN_PATH: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

settings = Settings()

def setup_gcp_credentials():
    if settings.GOOGLE_APPLICATION_CREDENTIALS:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS