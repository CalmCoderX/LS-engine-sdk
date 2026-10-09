"""Base engine server implementation"""

import asyncio
import logging
import time
import aiohttp
import json
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
import uvicorn

from .config import EngineConfig
from .connector import AsyncBackendConnector
from .output import extract_compliance_signature_for_task_metadata
from .models import (
    HealthResponse,
    ProcessingResponse,
)

logger = logging.getLogger(__name__)


class ProcessingContext:
    """Context object passed to processing methods"""
    
    def __init__(
        self,
        task_id: str,
        connector: AsyncBackendConnector,
        law_pack_file_paths: Optional[list] = None,
        title: Optional[str] = None,
        language: Optional[str] = None,
        library_version: Optional[str] = None,
        library_name: Optional[str] = None,
        engine_name: Optional[str] = None,
        engine_version: Optional[str] = None,
    ):
        self.task_id = task_id
        self.title = title  # Report/document title from backend (processing task title)
        self.law_pack_file_paths = [Path(p) for p in (law_pack_file_paths or [])]
        # Law pack name/version from backend (authoritative — do not infer from filenames in engines)
        def _norm_meta(v: Optional[Any]) -> Optional[str]:
            if v is None:
                return None
            t = str(v).strip()
            return t or None

        self.library_version = _norm_meta(library_version)
        self.library_name = _norm_meta(library_name)
        self.language = _norm_meta(language)
        self.engine_name = _norm_meta(engine_name)
        self.engine_version = _norm_meta(engine_version)
        self._connector = connector
        self._start_time = time.time()
    
    async def update_progress(self, percent: int, message: Optional[str] = None):
        """Send progress update to backend"""
        await self._connector.send_progress_update(
            task_id=self.task_id,
            percent=percent,
            message=message
        )
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed processing time in seconds"""
        return time.time() - self._start_time


class BaseEngine(ABC):
    """
    Base class for LexaShield processing engines
    
    Engine developers should extend this class and implement:
    - process_query(): Handle text query processing
    - process_file(): Handle file upload processing
    
    Optional overrides:
    - on_law_pack_received(): Hook called after law pack distribution
    - on_startup(): Hook called when engine starts
    - on_shutdown(): Hook called when engine stops
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        """
        Initialize the engine
        
        Args:
            config: Engine configuration (uses global config if not provided)
        """
        from .config import config as global_config
        self.config = config or global_config
        self.connector = AsyncBackendConnector(self.config)
        self.app = self._create_app()
        self._start_time = datetime.utcnow()
        self._active_tasks: int = 0
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration with file output"""
        import logging.handlers
        
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Determine log format
        if self.config.log_format.lower() == "json":
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        else:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Determine log file path
        if self.config.log_file:
            log_file = Path(self.config.log_file)
        else:
            # Default: logs folder in current working directory
            log_file = Path.home() / "lexashield/logs" / "engine.log"
        
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create file handler with rotation (10MB max, keep 5 backup files)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Optionally add console handler
        if self.config.log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_formatter = logging.Formatter(log_format)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Log startup message (after handlers are configured)
        logging.info(f"Logging configured - Level: {log_level}, File: {log_file}")
    
    def _create_app(self) -> FastAPI:
        """Create FastAPI application with all endpoints"""
        # Starlette 1.0+ removed add_event_handler; use lifespan (works on older Starlette too).
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await self._startup_handler()
            try:
                yield
            finally:
                await self._shutdown_handler()

        app = FastAPI(
            title=self.config.engine_name,
            version=self.config.engine_version,
            description="LexaShield Processing Engine",
            lifespan=lifespan,
        )

        # Register endpoints
        app.add_api_route("/", self._root_health_check, methods=["GET"])
        app.add_api_route("/health", self._health_check, methods=["GET"])
        app.add_api_route("/api/process", self._process_request, methods=["POST"])
        app.add_api_route("/api/results/{task_id}/{filename}", self._serve_result_file, methods=["GET"])
        app.add_api_route("/api/results/{task_id}/cleanup", self._cleanup_result_files, methods=["DELETE"])

        return app
    
    async def _startup_handler(self):
        """FastAPI startup handler"""
        logger.info(f"Starting {self.config.engine_name} v{self.config.engine_version}")
        logger.info(f"Backend URL: {self.config.backend_url}")
        await self.on_startup()
    
    async def _shutdown_handler(self):
        """FastAPI shutdown handler"""
        logger.info("Shutting down engine")
        await self.connector.close()
        await self.on_shutdown()
    
    # =========================================================================
    # BUILT-IN ENDPOINTS (Implemented)
    # =========================================================================
    
    async def _root_health_check(self) -> Dict[str, Any]:
        """Root endpoint for EBS health checks"""
        return {
            "status": "healthy",
            "service": self.config.engine_name,
            "version": self.config.engine_version,
            "backend_url": self.config.backend_url,
        }
    
    async def _health_check(self) -> HealthResponse:
        """Health check endpoint"""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version=self.config.engine_version,
            uptime_seconds=uptime
        )
    
    
    async def _process_request(
        self,
        background_tasks: BackgroundTasks,
        request: Request
    ) -> ProcessingResponse:
        """
        Accept processing request from backend
        
        Handles both JSON and multipart form data formats:
        - JSON: {..., "law_pack_urls": [...], "library_name", "library_version", "engine_name", "engine_version"} (platform metadata optional but recommended)
        - Form: task_id, query/file, law_pack_urls (JSON string)
        
        Law pack files are provided as presigned S3 URLs
        """
        try:
            content_type = request.headers.get("content-type", "").lower()
            task_id = None
            title = None  # Report title from backend (processing task title)
            query = None
            file_obj = None
            law_pack_urls_data = []
            law_pack_cache_max_entries_request = None
            library_version = None
            library_name = None
            engine_name = None
            engine_version = None
            language = None
            
            # Handle JSON format (from backend)
            if "application/json" in content_type:
                try:
                    body = await request.json()
                    task_id = body.get("task_id")
                    title = body.get("title")  # Report title from backend (processing task title)
                    query = body.get("query")
                    file_data = body.get("file")  # File as base64 encoded JSON object
                    law_pack_urls_data = body.get("law_pack_urls", [])
                    law_pack_cache_max_entries_request = body.get("law_pack_cache_max_entries")
                    library_version = body.get("library_version")
                    library_name = body.get("library_name")
                    engine_name = body.get("engine_name")
                    engine_version = body.get("engine_version")
                    language = body.get("lang")
                    
                    # If file is provided as base64, decode it and create a file-like object
                    if file_data:
                        import base64
                        
                        try:
                            file_content = base64.b64decode(file_data.get("content", ""))
                            filename = file_data.get("filename", "uploaded_file")
                            
                            # Create a BytesIO object that acts like a file
                            file_obj = BytesIO(file_content)
                            file_obj.filename = filename  # Store filename for later use
                            file_obj.content_type = file_data.get("content_type", "application/octet-stream")
                        except Exception as e:
                            raise HTTPException(status_code=400, detail=f"Invalid file data: {str(e)}")
                            
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON request: {str(e)}")
            
            # Handle multipart form data format (from validator)
            elif "multipart/form-data" in content_type:
                try:
                    form = await request.form()
                    task_id = form.get("task_id")
                    title = form.get("title")  # Report title from backend
                    query = form.get("query")
                    law_pack_urls_str = form.get("law_pack_urls")
                    file_obj = form.get("file")  # UploadFile object
                    library_version = form.get("library_version")
                    library_name = form.get("library_name")
                    engine_name = form.get("engine_name")
                    engine_version = form.get("engine_version")
                    language = form.get("lang")
                    
                    # Parse law_pack_urls JSON string
                    if law_pack_urls_str:
                        try:
                            import json as json_lib
                            law_pack_urls_data = json_lib.loads(law_pack_urls_str)
                        except Exception as e:
                            raise HTTPException(status_code=400, detail=f"Invalid law_pack_urls JSON: {str(e)}")
                    law_pack_cache_max_entries_request = form.get("law_pack_cache_max_entries")
                    
                    # Handle file upload
                    if file_obj and hasattr(file_obj, 'filename') and file_obj.filename:
                        # file_obj is already an UploadFile, use it directly
                        pass
                    else:
                        file_obj = None
                        
                except HTTPException:
                    raise
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid form data: {str(e)}")
            
            # Try to parse as JSON if content-type is not set (fallback)
            else:
                try:
                    body = await request.json()
                    task_id = body.get("task_id")
                    title = body.get("title")
                    query = body.get("query")
                    file_data = body.get("file")
                    law_pack_urls_data = body.get("law_pack_urls", [])
                    law_pack_cache_max_entries_request = body.get("law_pack_cache_max_entries")
                    library_version = body.get("library_version")
                    library_name = body.get("library_name")
                    engine_name = body.get("engine_name")
                    engine_version = body.get("engine_version")
                    language = body.get("lang")
                    
                    if file_data:
                        import base64
                        
                        try:
                            file_content = base64.b64decode(file_data.get("content", ""))
                            filename = file_data.get("filename", "uploaded_file")
                            file_obj = BytesIO(file_content)
                            file_obj.filename = filename
                            file_obj.content_type = file_data.get("content_type", "application/octet-stream")
                        except Exception as e:
                            raise HTTPException(status_code=400, detail=f"Invalid file data: {str(e)}")
                except:
                    # If JSON parsing fails, try form data
                    try:
                        form = await request.form()
                        task_id = form.get("task_id")
                        title = form.get("title")
                        query = form.get("query")
                        law_pack_urls_str = form.get("law_pack_urls")
                        file_obj = form.get("file")
                        library_version = form.get("library_version")
                        library_name = form.get("library_name")
                        engine_name = form.get("engine_name")
                        engine_version = form.get("engine_version")
                        language = form.get("lang")
                        
                        if law_pack_urls_str:
                            try:
                                import json as json_lib
                                law_pack_urls_data = json_lib.loads(law_pack_urls_str)
                            except Exception as e:
                                raise HTTPException(status_code=400, detail=f"Invalid law_pack_urls JSON: {str(e)}")
                        law_pack_cache_max_entries_request = form.get("law_pack_cache_max_entries")
                        if file_obj and hasattr(file_obj, 'filename') and file_obj.filename:
                            pass
                        else:
                            file_obj = None
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")
            
            # Validate required fields
            if not task_id:
                raise HTTPException(status_code=400, detail="task_id is required")
            if not query and not file_obj:
                raise HTTPException(status_code=400, detail="Either query or file is required")
            if not law_pack_urls_data:
                raise HTTPException(status_code=400, detail="law_pack_urls is required")
            
            # Backend sends law_pack_cache_max_entries; use it when present
            law_pack_cache_max_entries = (
                int(law_pack_cache_max_entries_request)
                if law_pack_cache_max_entries_request is not None
                else self.config.law_pack_cache_max_entries
            )
            
            # Download law pack files: use cache when cache_key is provided (store under law_packs/<cache_key>/)
            law_pack_file_paths = []
            law_pack_dir_fallback = self.config.results_storage_dir / task_id
            law_pack_dir_fallback.mkdir(parents=True, exist_ok=True)
            
            async with aiohttp.ClientSession() as session:
                for idx, law_pack_info in enumerate(law_pack_urls_data):
                    url = law_pack_info.get("url")
                    filename = law_pack_info.get("filename", f"law_pack_{idx}.jsonl")
                    cache_key = law_pack_info.get("cache_key")
                    
                    if not url:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Missing URL for law pack file {idx}"
                        )
                    
                    # Use law pack cache dir when cache_key present; otherwise per-task dir (backward compatible)
                    if cache_key:
                        cache_dir = self.config.law_pack_storage_dir / cache_key
                        law_pack_path = cache_dir / filename
                        if law_pack_path.exists():
                            law_pack_file_paths.append(law_pack_path)
                            try:
                                cache_dir.touch()
                            except Exception:
                                pass
                            logger.info(f"Using cached law pack file: {filename} (cache_key={cache_key})")
                            continue
                        cache_dir.mkdir(parents=True, exist_ok=True)
                    else:
                        law_pack_path = law_pack_dir_fallback / filename
                    
                    try:
                        async with session.get(url) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                raise HTTPException(
                                    status_code=500,
                                    detail=f"Failed to download law pack file from URL: {error_text}"
                                )
                            content = await response.read()
                            with open(law_pack_path, 'wb') as f:
                                f.write(content)
                            if cache_key:
                                try:
                                    (self.config.law_pack_storage_dir / cache_key).touch()
                                except Exception:
                                    pass
                            law_pack_file_paths.append(law_pack_path)
                            logger.info(f"Downloaded and saved law pack file: {filename} ({len(content)} bytes)")
                    except HTTPException:
                        raise
                    except Exception as e:
                        logger.error(f"Failed to download law pack file from {url}: {str(e)}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to download law pack file: {str(e)}"
                        )
            
            # Reject immediately if engine is already at CPU capacity
            if self._active_tasks >= self.config.max_concurrent_tasks:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Engine is busy processing another task "
                        f"({self._active_tasks}/{self.config.max_concurrent_tasks} active). "
                        "Retry when idle."
                    ),
                    headers={"Retry-After": "5"},
                )
            self._active_tasks += 1

            # Schedule processing in background
            if file_obj:
                # Save uploaded file (handle both BytesIO from base64 and UploadFile)
                filename = getattr(file_obj, 'filename', 'uploaded_file')
                file_path = self.config.results_storage_dir / task_id / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Read content (handle both BytesIO and UploadFile)
                if isinstance(file_obj, BytesIO):
                    # BytesIO from base64 decoded content
                    file_obj.seek(0)
                    content = file_obj.read()
                else:
                    # UploadFile from multipart form
                    content = await file_obj.read()
                
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                background_tasks.add_task(
                    self._process_file_background,
                    task_id,
                    str(file_path),
                    law_pack_file_paths,
                    title,
                    language,
                    law_pack_cache_max_entries,
                    library_version,
                    library_name,
                    engine_name,
                    engine_version,
                )
            else:
                background_tasks.add_task(
                    self._process_query_background,
                    task_id,
                    query,
                    law_pack_file_paths,
                    title,
                    language,
                    law_pack_cache_max_entries,
                    library_version,
                    library_name,
                    engine_name,
                    engine_version,
                )
            
            logger.info(f"Accepted processing request: task_id={task_id}, law_pack_files={len(law_pack_file_paths)}")
            
            return ProcessingResponse(
                task_id=task_id,
                status="accepted",
                message="Processing request accepted"
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error accepting processing request: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _serve_result_file(self, task_id: str, filename: str) -> FileResponse:
        """Serve result files for backend to download"""
        file_path = self.config.results_storage_dir / task_id / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    
    async def _cleanup_result_files(self, task_id: str) -> dict:
        """
        Clean up result files after backend has downloaded them
        
        This endpoint should be called by the backend after successfully
        downloading all result files to free up storage space.
        """
        try:
            result_dir = self.config.results_storage_dir / task_id
            
            if not result_dir.exists():
                raise HTTPException(status_code=404, detail="Task result directory not found")
            
            # Delete all files in the task directory
            deleted_files = []
            for file_path in result_dir.iterdir():
                if file_path.is_file():
                    deleted_files.append(file_path.name)
                    file_path.unlink()
            
            # Remove the directory itself
            result_dir.rmdir()
            
            logger.info(f"Cleaned up result files for task {task_id}: {deleted_files}")
            
            return {
                "message": "Result files cleaned up successfully",
                "task_id": task_id,
                "deleted_files": deleted_files
            }
        
        except Exception as e:
            logger.error(f"Error cleaning up result files for task {task_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    
    # =========================================================================
    # BACKGROUND PROCESSING
    # =========================================================================
    
    async def _process_query_background(
        self, task_id: str, query: str, law_pack_file_paths: List[Path], title: Optional[str] = None,
        language: Optional[str] = None,
        law_pack_cache_max_entries: Optional[int] = None,
        library_version: Optional[str] = None,
        library_name: Optional[str] = None,
        engine_name: Optional[str] = None,
        engine_version: Optional[str] = None,
    ):
        """Background task for query processing"""
        ctx = ProcessingContext(
            task_id,
            self.connector,
            law_pack_file_paths,
            title=title,
            language=language,
            library_version=library_version,
            library_name=library_name,
            engine_name=engine_name,
            engine_version=engine_version,
        )
        
        try:
            logger.info(f"Processing query for task {task_id} with {len(law_pack_file_paths)} law pack files")
            
            # Call user-implemented processing method
            results, process_metadata = await self.process_query(ctx, query)
            
            # Generate result files only when there are flag results; otherwise no files
            result_urls = await self._generate_result_files(task_id, results, ctx)

            # Merge processing metadata; when no files generated, include output so backend gets "no flags" result
            metadata = {
                "input_type": "query",
            }
            if isinstance(process_metadata, dict):
                metadata.update(process_metadata)
            sig = extract_compliance_signature_for_task_metadata(results)
            if sig:
                metadata["Compliance Signature"] = sig
            metadata.pop("processing_time", None)
            if not result_urls and results is not None:
                cleaned = self._remove_definitions_from_output(results)
                metadata["output"] = json.loads(json.dumps(cleaned, default=str))
            
            # Ensure completion webhook is emitted only after result files are on disk.
            await self._ensure_result_files_ready(task_id, result_urls)
            # Send completion notification
            await self.connector.send_completion(task_id, result_urls, metadata)
            
            logger.info(f"Task {task_id} completed successfully")
        
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            await self.connector.send_failure(task_id, str(e))
        
        finally:
            self._active_tasks = max(0, self._active_tasks - 1)
            await self._cleanup_law_pack_files(task_id)
            # Prune law pack cache to last N entries (after result sent)
            self._prune_law_pack_cache(law_pack_cache_max_entries or self.config.law_pack_cache_max_entries)
    
    async def _process_file_background(
        self, task_id: str, file_path: str, law_pack_file_paths: List[Path], title: Optional[str] = None,
        language: Optional[str] = None,
        law_pack_cache_max_entries: Optional[int] = None,
        library_version: Optional[str] = None,
        library_name: Optional[str] = None,
        engine_name: Optional[str] = None,
        engine_version: Optional[str] = None,
    ):
        """Background task for file processing"""
        ctx = ProcessingContext(
            task_id,
            self.connector,
            law_pack_file_paths,
            title=title,
            language=language,
            library_version=library_version,
            library_name=library_name,
            engine_name=engine_name,
            engine_version=engine_version,
        )
        
        try:
            logger.info(f"Processing file for task {task_id}: {file_path} with {len(law_pack_file_paths)} law pack files")
            
            # Call user-implemented processing method
            results, process_metadata = await self.process_file(ctx, file_path)
            
            # Generate result files only when there are flag results; otherwise no files
            result_urls = await self._generate_result_files(task_id, results, ctx)
            
            # Merge processing metadata; when no files generated, include output so backend gets "no flags" result
            metadata = {
                "input_type": "file",
            }
            if isinstance(process_metadata, dict):
                metadata.update(process_metadata)
            sig = extract_compliance_signature_for_task_metadata(results)
            if sig:
                metadata["Compliance Signature"] = sig
            metadata.pop("processing_time", None)
            if not result_urls and results is not None:
                cleaned = self._remove_definitions_from_output(results)
                metadata["output"] = json.loads(json.dumps(cleaned, default=str))
            
            # Ensure completion webhook is emitted only after result files are on disk.
            await self._ensure_result_files_ready(task_id, result_urls)
            # Send completion notification
            await self.connector.send_completion(task_id, result_urls, metadata)
            
            logger.info(f"Task {task_id} completed successfully")
        
        except Exception as e:
            logger.error(f"Task {task_id} failed: {str(e)}")
            await self.connector.send_failure(task_id, str(e))
        
        finally:
            self._active_tasks = max(0, self._active_tasks - 1)
            await self._cleanup_law_pack_files(task_id)
            self._prune_law_pack_cache(law_pack_cache_max_entries or self.config.law_pack_cache_max_entries)
    
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
        Enrich the output dict (in place) with Report Metadata: Analysis ID = task_id,
        Report Generated on = format_report_datetime().
        When the backend sends library_version / library_name / engine_name / engine_version,
        those values override engine defaults (authoritative for PDF and JSON).
        """
        try:
            from .output import format_report_datetime, refresh_output_signature
        except ImportError:
            return
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
        # Prefer library language for report display (labels, PDF); fall back to Engine language
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

    def _has_flag_results(self, results: Any) -> bool:
        """
        Return True if the output contains at least one flag result (so we generate files).
        Kept for analytics/branching, but file generation now proceeds even when False
        so users can still download the report (with the no-flag explanation pages).
        """
        output_dict = None
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            if isinstance(first, dict) and ("Report Metadata" in first or "Results" in first):
                output_dict = first
        elif isinstance(results, dict) and ("Report Metadata" in results or "Results" in results):
            output_dict = results
        if output_dict is None:
            return False
        results_list = output_dict.get("Results") or output_dict.get("results") or []
        if isinstance(results_list, list) and len(results_list) > 0:
            return True
        summary = output_dict.get("Summary") or output_dict.get("summary") or {}
        total = summary.get("Total Detections") or summary.get("total_detections") or summary.get("Total Flags") or summary.get("total_flags")
        if total is not None and int(total) > 0:
            return True
        return False

    async def _generate_result_files(self, task_id: str, results: Any, ctx: ProcessingContext) -> Dict[str, str]:
        """
        Generate the result JSON, even with no flags, and return its URL.
        """
        # Use task_id as Analysis ID and set Report Generated on (in place)
        self._enrich_output_with_report_metadata(
            results,
            task_id,
            library_version=ctx.library_version,
            library_name=ctx.library_name,
            engine_name=ctx.engine_name,
            engine_version=ctx.engine_version,
        )

        result_dir = self.config.results_storage_dir / task_id
        result_dir.mkdir(parents=True, exist_ok=True)
        result_urls = {}
        # Send path only (no host); backend uses its own engine base URL to download

        # Generate JSON result
        json_content = self._generate_json_result(results)
        json_path = result_dir / "result.json"
        json_path.write_text(json_content, encoding='utf-8')
        result_urls["json_url"] = f"/api/results/{task_id}/result.json"

        return result_urls

    async def _ensure_result_files_ready(self, task_id: str, result_urls: Dict[str, str]) -> None:
        """
        Verify referenced result files exist before sending completion webhook.
        This keeps completion semantics strict and avoids backend download races.
        """
        if not result_urls:
            return

        url_to_filename = {
            "json_url": "result.json",
            "html_url": "result.html",
            "pdf_url": "result.pdf",
            "excel_url": "result.xlsx",
        }
        result_dir = self.config.results_storage_dir / task_id
        max_attempts = 5

        for key, _url in result_urls.items():
            filename = url_to_filename.get(key)
            if not filename:
                continue

            file_path = result_dir / filename
            for attempt in range(1, max_attempts + 1):
                if file_path.exists() and file_path.is_file():
                    # Non-empty check for binary/text output files.
                    try:
                        if file_path.stat().st_size > 0:
                            break
                    except OSError:
                        pass

                if attempt == max_attempts:
                    raise RuntimeError(
                        f"Result file not ready for completion webhook: {file_path}"
                    )

                await asyncio.sleep(0.2)
    
    def _generate_json_result(self, results: Any) -> str:
        """
        Generate JSON result file (can be overridden by subclasses)
        
        Args:
            results: Processing results (list, dict, or any serializable data)
            
        Returns:
            JSON string representation of the results (with Definitions removed)
        """
        cleaned_results = self._remove_definitions_from_output(results)

        if isinstance(cleaned_results, list):
            normalized_results = cleaned_results
        else:
            normalized_results = [cleaned_results]

        return json.dumps(normalized_results, indent=2, ensure_ascii=False, default=str)
    
    def _remove_definitions_from_output(self, results: Any) -> Any:
        """
        Remove Definitions from the JSON output. The PDF renderer adds them.
        
        Args:
            results: Processing results (list or dict)
            
        Returns:
            Results with Definitions removed
        """
        if isinstance(results, dict):
            # Create a copy without Definitions
            cleaned = {k: v for k, v in results.items() if k != "Definitions"}
            return cleaned
        elif isinstance(results, list) and len(results) > 0:
            # If it's a list with a dict containing Definitions, remove it
            cleaned_list = []
            for item in results:
                if isinstance(item, dict):
                    cleaned_item = {k: v for k, v in item.items() if k != "Definitions"}
                    cleaned_list.append(cleaned_item)
                else:
                    cleaned_list.append(item)
            return cleaned_list
        return results
    
    # =========================================================================
    # ABSTRACT METHODS (Must be implemented by subclasses)
    # =========================================================================
    
    @abstractmethod
    async def process_query(self, ctx: ProcessingContext, query: str) -> tuple:
        """
        Process a text query
        
        Args:
            ctx: Processing context (use ctx.update_progress() to send updates)
            query: Text query to process
            
        Returns:
            Tuple: (results, metadata) where:
            - results: The processing results (list, dict, or any serializable data)
            - metadata: Dictionary with processing metadata (e.g., matches_found, scan_timestamp)
            
        Example:
            async def process_query(self, ctx, query):
                await ctx.update_progress(25, "Analyzing query...")
                results = analyze(query)
                await ctx.update_progress(100, "Complete")
                metadata = {
                    "matches_found": len(results),
                    "scan_timestamp": datetime.now(timezone.utc).isoformat()
                }
                return results, metadata
        """
        pass
    
    @abstractmethod
    async def process_file(self, ctx: ProcessingContext, file_path: str) -> tuple:
        """
        Process an uploaded file
        
        Args:
            ctx: Processing context (use ctx.update_progress() to send updates)
            file_path: Path to uploaded file
            
        Returns:
            Tuple: (results, metadata) where:
            - results: The processing results (list, dict, or any serializable data)
            - metadata: Dictionary with processing metadata (e.g., matches_found, scan_timestamp)
            
        Example:
            async def process_file(self, ctx, file_path):
                await ctx.update_progress(30, "Reading file...")
                with open(file_path, 'r') as f:
                    content = f.read()
                await ctx.update_progress(70, "Analyzing...")
                results = analyze(content)
                await ctx.update_progress(100, "Complete")
                metadata = {
                    "matches_found": len(results),
                    "scan_timestamp": datetime.now(timezone.utc).isoformat()
                }
                return results, metadata
        """
        pass
    
    # =========================================================================
    # OPTIONAL HOOKS (Can be overridden by subclasses)
    # =========================================================================
    
    async def on_startup(self):
        """Hook called when engine starts"""
        pass
    
    async def on_shutdown(self):
        """Hook called when engine stops"""
        pass
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    async def _cleanup_law_pack_files(self, task_id: str):
        """Clean up temporary law pack files after processing (per-task dir under results; cache lives under law_packs/)"""
        try:
            law_pack_dir = self.config.results_storage_dir / task_id / "law_packs"
            if law_pack_dir.exists():
                import shutil
                shutil.rmtree(law_pack_dir)
                logger.info(f"Cleaned up law pack files for task {task_id}")
        except Exception as e:
            logger.warning(f"Failed to clean up law pack files for task {task_id}: {str(e)}")
    
    def _prune_law_pack_cache(self, max_entries: int):
        """Keep only the last max_entries law pack cache dirs (by mtime); remove the rest."""
        try:
            root = self.config.law_pack_storage_dir
            if not root.exists():
                return
            subdirs = [p for p in root.iterdir() if p.is_dir()]
            if len(subdirs) <= max_entries:
                return
            # Sort by mtime descending (most recently used first); keep first max_entries, delete rest
            subdirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            import shutil
            for p in subdirs[max_entries:]:
                try:
                    shutil.rmtree(p)
                    logger.info(f"Pruned law pack cache: removed {p.name}")
                except Exception as e:
                    logger.warning(f"Failed to prune law pack cache dir {p}: {e}")
        except Exception as e:
            logger.warning(f"Failed to prune law pack cache: {e}")
    
    def run(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Run the engine server
        
        Args:
            host: Host to bind to (uses config if not provided)
            port: Port to bind to (uses config if not provided)
        """
        host = host or self.config.engine_host
        port = port or self.config.engine_port
        
        logger.info(f"Starting engine server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level=self.config.log_level.lower()
        )
