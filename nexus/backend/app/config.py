from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Nexus AI Trading"
    db_url: str = "sqlite:///./nexus.db"
    jwt_secret: str  # MUST match env var name (lowercase)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # IMPORTANT: ignore extra env vars safely
    )

settings = Settings()


