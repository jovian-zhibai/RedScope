from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
import warnings


class Settings(BaseSettings):
    app_name: str = "RedScope"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://redscope:redscope_dev_2026@localhost:5432/redscope"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = ""
    access_token_expire_minutes: int = 480
    algorithm: str = "HS256"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    scan_output_dir: str = "/app/output"
    plugins_dir: str = "/app/plugins"
    max_upload_size: int = 50 * 1024 * 1024
    max_concurrent_scans: int = 10
    max_targets_per_scan: int = 500

    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    notify_webhook_url: str = ""
    notify_channel: str = "wecom"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if not self.secret_key or len(self.secret_key) < 32:
                raise ValueError("生产环境 SECRET_KEY 必须设置且长度>=32位")
            if "dev" in self.secret_key.lower() or "change" in self.secret_key.lower():
                raise ValueError("生产环境 SECRET_KEY 不能使用默认值")
            if self.debug:
                self.debug = False
        if not self.secret_key:
            self.secret_key = "redscope-dev-only-do-not-use-in-production"
            warnings.warn(
                "\n⚠️  WARNING: 使用默认开发密钥！请设置 SECRET_KEY 环境变量。\n"
                "   当前密钥仅适用于本地开发，切勿用于生产环境。\n",
                stacklevel=2,
            )
        return self

    def get_cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
