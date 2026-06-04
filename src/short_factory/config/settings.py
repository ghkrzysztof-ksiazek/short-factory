from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://short_factory:short_factory@localhost:5432/short_factory"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "short-factory"
    s3_region: str = "us-east-1"

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    grok_api_key: str = ""
    grok_api_base: str = "https://api.x.ai/v1"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "short-factory/0.1"

    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_client_secrets_file: str = ""
    youtube_refresh_token: str = ""

    default_subtitle_style: dict = Field(
        default_factory=lambda: {
            "fontname": "Arial",
            "fontsize": 52,
            "primary_colour": "&H00FFFFFF",
            "margin_v": 120,
        }
    )

    tts_provider: str = "openai"
    elevenlabs_api_key: str = ""
    openai_tts_voice: str = "alloy"

    pexels_api_key: str = ""

    log_level: str = "INFO"
    environment: str = "development"
    render_dir: str = "/tmp/renders"
    virality_threshold: float = 0.6
    topics_per_scrape: int = 50


settings = Settings()
