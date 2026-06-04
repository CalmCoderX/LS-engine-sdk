"""Configuration management for LexaShield engines"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConfig(BaseSettings):
    """Engine configuration loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars (e.g. from backend .env when running validator in same dir)
    )
    
    # Backend connection
    backend_url: str = "http://localhost:8000"
    
    # Engine server settings
    engine_host: str = "0.0.0.0"
    engine_port: int = 8080
    engine_name: str = "LexaShield Engine"
    engine_version: str = "1.0.0"
    
    # Storage directories
    results_storage_dir: Path = Path.home() / "lexashield/results"
    law_pack_storage_dir: Path = Path.home() / "lexashield/law_packs"
    law_pack_cache_max_entries: int = 30
    
    # Connection settings
    request_timeout: int = 30  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # or "text"
    log_file: Optional[str] = None  # If None, logs to ./logs/engine.log (relative to engine folder)
    log_to_console: bool = True  # Also output to console
    
    # Performance — one in-flight processing job per worker process (reject with HTTP 429 when busy).
    max_concurrent_tasks: int = 1
    cleanup_results_after_hours: int = 24
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create storage directories if they don't exist
        self.results_storage_dir.mkdir(parents=True, exist_ok=True)
        self.law_pack_storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Set default log file if not specified (store as string for serialization)
        if self.log_file is None:
            # Create logs directory in current working directory (where engine is run from)
            log_dir = Path.home() / "lexashield/logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = str(log_dir / "engine.log")
    
    @property
    def webhook_base_url(self) -> str:
        """Base URL for webhook endpoints"""
        return f"{self.backend_url.rstrip('/')}/api/engine-webhooks"
    
    @property
    def progress_webhook_url(self) -> str:
        """URL for progress updates"""
        return f"{self.webhook_base_url}/processing/update"
    
    @property
    def completion_webhook_url(self) -> str:
        """URL for completion notifications"""
        return f"{self.webhook_base_url}/processing/complete"
    
    @property
    def engine_base_url(self) -> str:
        """Public URL of this engine (for result file serving)"""
        host = self.engine_host
        if host == "0.0.0.0":
            host = "localhost"
        return os.getenv("ENGINE_PUBLIC_URL", f"http://{host}:{self.engine_port}")


# Global config instance
config = EngineConfig()
