"""
Configuration management for the Expert Interviewers system
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Database
    database_url: str = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")

    # Redis
    redis_url: str = Field(alias="REDIS_URL")

    # Twilio
    twilio_account_sid: str = Field(alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(alias="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: str = Field(alias="TWILIO_WEBHOOK_URL")

    # Deepgram (STT)
    deepgram_api_key: str = Field(alias="DEEPGRAM_API_KEY")

    # ElevenLabs (TTS)
    elevenlabs_api_key: str = Field(alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field(alias="ELEVENLABS_VOICE_ID")

    # Anthropic Claude
    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", alias="ANTHROPIC_MODEL")

    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")

    # Security
    secret_key: str = Field(alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")

    # Monitoring
    enable_prometheus: bool = Field(default=True, alias="ENABLE_PROMETHEUS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Research Settings
    max_concurrent_interviews: int = Field(default=100, alias="MAX_CONCURRENT_INTERVIEWS")
    default_interview_timeout_minutes: int = Field(default=60, alias="DEFAULT_INTERVIEW_TIMEOUT_MINUTES")
    max_follow_ups_per_question: int = Field(default=3, alias="MAX_FOLLOW_UPS_PER_QUESTION")
    silence_detection_seconds: int = Field(default=5, alias="SILENCE_DETECTION_SECONDS")

    # Compliance
    enable_call_recording: bool = Field(default=True, alias="ENABLE_CALL_RECORDING")
    data_retention_days: int = Field(default=90, alias="DATA_RETENTION_DAYS")
    gdpr_compliance: bool = Field(default=True, alias="GDPR_COMPLIANCE")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
