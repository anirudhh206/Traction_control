"""Configuration Management with Type Safety."""

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation."""
    
    model_config = SettingsConfigDict(
        env_file='../.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # ANTHROPIC
    anthropic_api_key: str = Field(..., min_length=1)
    
    # SUPABASE
    supabase_url: str = Field(..., min_length=1)
    supabase_key: str = Field(..., min_length=1)
    
    # REDDIT
    reddit_client_id: Optional[str] = Field(default=None)
    reddit_client_secret: Optional[str] = Field(default=None)
    reddit_username: Optional[str] = Field(default=None)
    reddit_password: Optional[str] = Field(default=None)
    reddit_user_agent: str = Field(default="RepEscrow:v1.0.0")
    
    # DISCORD
    discord_bot_token: Optional[str] = Field(default=None)
    
    # TELEGRAM
    telegram_bot_token: Optional[str] = Field(default=None)
    
    # SENDGRID (renamed to avoid conflicts)
    sendgrid_api_key: Optional[str] = Field(default=None)
    sendgrid_from_email: str = Field(default="hello@repescrow.xyz")
    sendgrid_from_name: str = Field(default="RepEscrow Team")
    
    # TWITTER
    twitter_username: Optional[str] = Field(default=None)
    twitter_password: Optional[str] = Field(default=None)
    twitter_email: Optional[str] = Field(default=None)
    
    # PRODUCT
    product_name: str = Field(default="RepEscrow")
    product_url: str = Field(default="https://repescrow.xyz")
    product_tagline: str = Field(default="Reputation-weighted escrow for Web3 service providers")
    
    # MONITORING
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    environment: Literal["development", "staging", "production"] = Field(default="development")
    
    # RATE LIMITS
    max_reddit_posts_per_day: int = Field(default=10, ge=1, le=50)
    max_reddit_comments_per_day: int = Field(default=20, ge=1, le=100)
    max_discord_messages_per_day: int = Field(default=30, ge=1, le=100)
    max_telegram_messages_per_day: int = Field(default=25, ge=1, le=100)
    max_emails_per_day: int = Field(default=100, ge=1, le=100)
    max_twitter_posts_per_day: int = Field(default=6, ge=1, le=20)
    max_twitter_replies_per_day: int = Field(default=100, ge=1, le=200)
    
    # AGENTS
    enable_reddit_agent: bool = Field(default=True)
    enable_discord_agent: bool = Field(default=True)
    enable_telegram_agent: bool = Field(default=True)
    enable_email_agent: bool = Field(default=True)
    enable_twitter_agent: bool = Field(default=True)
    enable_forum_agent: bool = Field(default=True)
    enable_community_agent: bool = Field(default=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings