"""Engine logging settings from environment variables."""

import os
from pathlib import Path


class EngineConfig:
    """LOG_LEVEL, LOG_FILE and LOG_TO_CONSOLE."""

    def __init__(self) -> None:
        self.log_level = os.environ.get("LOG_LEVEL") or "INFO"
        self.log_file = os.environ.get("LOG_FILE") or str(Path.home() / "lexashield/logs" / "engine.log")
        self.log_to_console = os.environ.get("LOG_TO_CONSOLE", "true").strip().lower() not in ("0", "false", "no", "off")
