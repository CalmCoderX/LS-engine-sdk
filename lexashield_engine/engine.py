"""BaseEngine and ProcessingContext."""

import json
import logging
import logging.handlers
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional

from .config import EngineConfig
from .output import format_report_datetime, refresh_output_signature

logger = logging.getLogger(__name__)


class ProcessingContext:
    """Job details passed to process_query and process_file."""

    def __init__(
        self,
        task_id: str,
        law_pack_file_paths: List[Path],
        title: str = "",
        language: Optional[str] = None,
        progress_publisher: Optional[Callable[[int, str], Awaitable[None]]] = None,
    ) -> None:
        self.task_id = task_id
        self.law_pack_file_paths = [Path(p) for p in law_pack_file_paths]
        self.title = title
        self.language = language
        self._progress_publisher = progress_publisher
        self._started = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._started

    async def update_progress(self, percent: int, message: str = "") -> None:
        """Log progress and send it to the backend."""
        logging.getLogger("worker_context").info(
            '{"event": "progress", "taskId": "%s", "percent": %d, "message": "%s"}',
            self.task_id,
            percent,
            str(message).replace('"', "'"),
        )
        if self._progress_publisher is not None:
            await self._progress_publisher(percent, message)


class BaseEngine(ABC):
    """
    Base class for engines.

    Implement process_query() and process_file(). Load models in on_startup();
    SQSWorker calls it once before polling.
    """

    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Root logger writes to a rotating file and, by default, the console."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_file = Path(self.config.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers.clear()

        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)

        if self.config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(console_handler)

        logging.info(f"Logging configured - Level: {log_level}, File: {log_file}")

    async def on_startup(self):
        """Load models and other dependencies. Called once before the first job."""

    @abstractmethod
    async def process_query(self, ctx: ProcessingContext, query: str) -> tuple:
        """Analyse text. Return (results, metadata)."""

    @abstractmethod
    async def process_file(self, ctx: ProcessingContext, file_path: str) -> tuple:
        """Analyse a downloaded input file. Return (results, metadata)."""

    def _enrich_output_with_report_metadata(
        self,
        results: Any,
        task_id: str,
        library_version: Optional[str] = None,
        library_name: Optional[str] = None,
        engine_name: Optional[str] = None,
        engine_version: Optional[str] = None,
    ) -> None:
        """
        Set Report Metadata in place: Analysis ID = task_id and Report Generated on.
        Engine and library name/version from the backend override engine defaults.
        """
        output_dict = None
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            if isinstance(first, dict) and ("Report Metadata" in first or "Results" in first):
                output_dict = first
        elif isinstance(results, dict) and ("Report Metadata" in results or "Results" in results):
            output_dict = results
        if output_dict is None:
            return
        if "Report Metadata" not in output_dict:
            output_dict["Report Metadata"] = {}
        rm = output_dict["Report Metadata"]
        rm["Analysis ID"] = task_id
        report_language = (
            (output_dict.get("Library") or {}).get("Language")
            or output_dict.get("Engine", {}).get("Language")
            or rm.get("Language")
            or "en-US"
        )
        session_ts = output_dict.get("Session", {}).get("Timestamp UTC") or output_dict.get("Processing", {}).get("Completed At")
        rm["Report Generated on"] = format_report_datetime(
            session_ts,
            timezone_name="UTC",
            language=str(report_language),
        )
        backend_platform_applied = False

        def _ensure_engine_dict() -> None:
            if "Engine" not in output_dict or not isinstance(output_dict.get("Engine"), dict):
                output_dict["Engine"] = {}

        if engine_name:
            _ensure_engine_dict()
            output_dict["Engine"]["Name"] = engine_name
            rm["Engine Name"] = engine_name
            backend_platform_applied = True
        if engine_version:
            _ensure_engine_dict()
            output_dict["Engine"]["Version"] = engine_version
            rm["Engine Version"] = engine_version
            backend_platform_applied = True
        elif engine_name:
            _ensure_engine_dict()
            output_dict["Engine"]["Version"] = "N/A"
            rm["Engine Version"] = "N/A"
            backend_platform_applied = True

        if library_name:
            rm["Library Used"] = library_name
            if "Library" not in output_dict:
                output_dict["Library"] = {}
            if isinstance(output_dict["Library"], dict):
                output_dict["Library"]["Name"] = library_name
            backend_platform_applied = True
        elif "Library Used" not in rm and output_dict.get("Library", {}).get("Name"):
            rm["Library Used"] = output_dict["Library"]["Name"]
        if library_version:
            rm["Library Version"] = library_version
            if "Library" not in output_dict:
                output_dict["Library"] = {}
            if isinstance(output_dict["Library"], dict):
                output_dict["Library"]["Version"] = library_version
            if "Traceability" not in output_dict:
                output_dict["Traceability"] = {}
            if isinstance(output_dict["Traceability"], dict):
                output_dict["Traceability"]["Library Version"] = library_version
            backend_platform_applied = True
        # Prefer the library language for report display; fall back to the engine language.
        if "Language" not in rm:
            lib_lang = (output_dict.get("Library") or {}).get("Language")
            if lib_lang:
                rm["Language"] = lib_lang
            elif output_dict.get("Engine", {}).get("Language"):
                rm["Language"] = output_dict["Engine"]["Language"]
        if backend_platform_applied:
            try:
                refresh_output_signature(output_dict)
            except Exception:
                logger.debug("Signature refresh skipped after backend platform metadata", exc_info=True)

    def _generate_json_result(self, results: Any) -> str:
        """result.json content: a list of report objects without Definitions."""
        cleaned_results = self._remove_definitions_from_output(results)

        if isinstance(cleaned_results, list):
            normalized_results = cleaned_results
        else:
            normalized_results = [cleaned_results]

        return json.dumps(normalized_results, indent=2, ensure_ascii=False, default=str)

    def _remove_definitions_from_output(self, results: Any) -> Any:
        """Drop Definitions from the output. The backend PDF renderer adds them."""
        if isinstance(results, dict):
            return {k: v for k, v in results.items() if k != "Definitions"}
        if isinstance(results, list) and len(results) > 0:
            cleaned_list = []
            for item in results:
                if isinstance(item, dict):
                    cleaned_list.append({k: v for k, v in item.items() if k != "Definitions"})
                else:
                    cleaned_list.append(item)
            return cleaned_list
        return results
