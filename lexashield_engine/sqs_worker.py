"""
SQSWorker — shared ECS/Fargate worker loop for all Lexa engine types.

Each engine's worker.py sets the model-cache env vars, instantiates its own SDK
class, then hands control to this class:

    sdk = LawEngineSDK()
    worker = SQSWorker(engine_type="law", queue_env_var="SQS_LAW_QUEUE_URL")
    asyncio.run(worker.run(sdk))

Required environment variables (set by the caller before importing):
    SENTENCE_TRANSFORMERS_HOME  Model cache directory     (default: /app/models)
    SQS_<ENGINE>_QUEUE_URL      Engine-specific SQS queue (name passed via queue_env_var)
    SQS_TASK_QUEUE_URL          Backend main queue (worker completion messages)
    S3_BUCKET_NAME              Result storage bucket
    AWS_DEFAULT_REGION          (default: us-east-1)
    S3_RESULTS_FOLDER           (default: results)
    SQS_VISIBILITY_TIMEOUT      Seconds (default: 300)

The worker stores the analysis JSON only; the backend generates PDFs.

Timings in worker_completion metadata (ms):
    processing_time_ms     law pack download + analysis
    analysis_time_ms       process_query / process_file
    law_pack_download_ms
    input_download_ms      file jobs only, else 0
    result_upload_ms       metadata enrichment + JSON upload
    engine_job_ms          whole job
    model_load_time_ms     model load at container start
Also pdf_generation ("on_demand") and sdk_version.
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Awaitable

import boto3

from ._version import __version__ as SDK_VERSION
from .output import extract_compliance_signature_for_task_metadata

# Written to task metadata: the engine does not generate the PDF.
PDF_GENERATION_MODE = "on_demand"


def _elapsed_ms(started: float) -> int:
    """Milliseconds since a time.monotonic() reading."""
    return int((time.monotonic() - started) * 1000)


class SQSWorker:
    """
    Generic SQS polling loop shared by all engine worker containers.

        Lifecycle (called by run()):
      1. Validate local model directory — fail fast if missing or empty.
      2. Call sdk.on_startup() to load all inference dependencies into memory (once).
         Engines must complete heavy setup here; ``worker_ready`` is logged only after
         ``on_startup`` returns (see ``run()``).
      3. Poll the engine-specific SQS queue continuously.
      4. For each message:
           - Download law pack JSONL files from S3.
           - Run inference via sdk.process_query / sdk.process_file.
           - Save result JSON to S3.
           - Send worker_completion, with timings, to the backend SQS queue.
           - Delete the engine queue message only after success.
      5. On job failure: send worker_completion(status=failed),
         do NOT delete — SQS retries / DLQ handles it.
    """

    def __init__(
        self,
        engine_type: str,
        queue_env_var: str,
        logger_name: Optional[str] = None,
    ) -> None:
        """
        Args:
            engine_type:   'law' | 'iso' | 'standard'  (used in logs and metadata)
            queue_env_var: Name of the env var that holds the engine SQS queue URL,
                           e.g. 'SQS_LAW_QUEUE_URL'
            logger_name:   Optional override for the Python logger name.
        """
        self.engine_type = engine_type
        self.queue_env_var = queue_env_var
        self.logger = logging.getLogger(logger_name or f"{engine_type}_worker")

    # ── Model cache validation ────────────────────────────────────────────────

    def _validate_model_directory(self, model_dir: str) -> None:
        """Fail fast if the model directory is missing or empty."""
        model_path = Path(model_dir)
        if not model_path.exists():
            raise RuntimeError(
                f"Model directory not found: {model_dir}. "
                "Ensure models are available in the container image or mounted path."
            )
        items = list(model_path.iterdir())
        if not items:
            raise RuntimeError(
                f"Model directory is empty: {model_dir}. "
                "Preload models during image build or provide a populated model volume."
            )
        self.logger.info(
            '{"event": "model_cache_validated", "modelDir": "%s", "itemCount": %d}',
            model_dir, len(items),
        )

    # ── Context stub ──────────────────────────────────────────────────────────

    class _WorkerContext:
        """
        Duck-typed replacement for lexashield_engine.ProcessingContext.
        Satisfies the interface the engine SDK calls without an HTTP layer.
        """
        def __init__(
            self,
            task_id: str,
            task_db_id: int,
            law_pack_file_paths: List[Path],
            title: str = "",
            language: Optional[str] = None,
            progress_publisher: Optional[Callable[[int, str], Awaitable[None]]] = None,
        ) -> None:
            self.task_id = task_id
            self.task_db_id = task_db_id
            self.law_pack_file_paths = [Path(p) for p in law_pack_file_paths]
            self.title = title
            self.language = language
            self._progress_publisher = progress_publisher
            self._started = time.monotonic()

        @property
        def elapsed_seconds(self) -> float:
            return time.monotonic() - self._started

        async def update_progress(self, percent: int, message: str = "") -> None:
            # Progress is logged; live DB updates are handled by the
            # recovery job on the backend side.
            logging.getLogger("worker_context").info(
                '{"event": "progress", "taskId": "%s", "percent": %d, "message": "%s"}',
                self.task_id,
                percent,
                str(message).replace('"', "'"),
            )
            if self._progress_publisher is not None:
                await self._progress_publisher(percent, message)

    # ── Job processing ────────────────────────────────────────────────────────

    @staticmethod
    def _download_s3_file(s3_client: Any, bucket: str, key: str, dest: Path) -> None:
        s3_client.download_file(bucket, key, str(dest))

    async def _process_job(
        self,
        sdk: Any,
        body: Dict[str, Any],
        sqs_client: Any,
        backend_queue_url: str,
        s3_client: Any,
        s3_bucket: str,
        results_folder: str,
        model_load_time_ms: int,
    ) -> Dict[str, Any]:
        """
        Execute one job from SQS.  Returns the completion payload dict.
        Raises on unrecoverable errors so the caller can decide whether to
        delete the SQS message or leave it for retry / DLQ.
        """
        task_id: str = body["task_id"]
        task_db_id: int = body["task_db_id"]
        input_type: str = body["input_type"]
        law_pack_files_meta: List[Dict] = body.get("law_pack_files", [])
        title: str = body.get("title", task_id)
        language: Optional[str] = body.get("lang")

        t_start = time.monotonic()
        input_download_ms = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Download law pack JSONL files from S3 using boto3 credentials.
            # Using the s3_key directly avoids presigned-URL expiry issues.
            t_phase = time.monotonic()
            local_law_pack_paths: List[Path] = []
            for lp in law_pack_files_meta:
                filename = lp["filename"]
                s3_law_pack_key = lp["s3_key"]
                local_path = tmp / filename
                await asyncio.to_thread(
                    self._download_s3_file, s3_client, s3_bucket, s3_law_pack_key, local_path
                )
                local_law_pack_paths.append(local_path)
                self.logger.info(
                    '{"event": "law_pack_downloaded", "taskId": "%s", "filename": "%s", "s3Key": "%s"}',
                    task_id, filename, s3_law_pack_key,
                )
            law_pack_download_ms = _elapsed_ms(t_phase)

            async def _publish_progress(percent: int, message: str = "") -> None:
                progress_payload = {
                    "message_type": "worker_progress",
                    "task_id": task_id,
                    "task_db_id": task_db_id,
                    "status": "processing",
                    "percent": max(0, min(100, int(percent))),
                    "message": message,
                }
                await asyncio.to_thread(
                    sqs_client.send_message,
                    QueueUrl=backend_queue_url,
                    MessageBody=json.dumps(progress_payload, default=str),
                )

            ctx = self._WorkerContext(
                task_id,
                task_db_id,
                local_law_pack_paths,
                title,
                language,
                _publish_progress,
            )

            if input_type == "query":
                t_phase = time.monotonic()
                results, metadata = await sdk.process_query(ctx, body["input_query"])
                analysis_time_ms = _elapsed_ms(t_phase)

            elif input_type == "file":
                s3_key: str = body["input_file_s3_key"]
                local_input = tmp / (body.get("input_file_name") or "input_file")
                t_phase = time.monotonic()
                await asyncio.to_thread(
                    s3_client.download_file, s3_bucket, s3_key, str(local_input)
                )
                input_download_ms = _elapsed_ms(t_phase)
                t_phase = time.monotonic()
                results, metadata = await sdk.process_file(ctx, str(local_input))
                analysis_time_ms = _elapsed_ms(t_phase)

            else:
                raise ValueError(f"Unknown input_type: {input_type!r}")

            # Keep this measurement point: reports compare it with SDK 2.x jobs.
            processing_time_ms = _elapsed_ms(t_start)
            t_phase = time.monotonic()

            # Enrich output in-place: sets Analysis ID = task_id, Report Generated on,
            # and overrides engine/library metadata with authoritative backend values.
            # Mirrors what BaseEngine._generate_result_files does in the HTTP path.
            sdk._enrich_output_with_report_metadata(
                results,
                task_id,
                library_version=body.get("library_version"),
                library_name=body.get("library_name"),
                engine_name=body.get("engine_name"),
                engine_version=body.get("engine_version"),
            )

            if not isinstance(metadata, dict):
                metadata = {}
            sig = extract_compliance_signature_for_task_metadata(results)
            if sig:
                metadata["Compliance Signature"] = sig

            # ── Upload JSON result to S3 ───────────────────────────────────────
            result_json_bytes = sdk._generate_json_result(results).encode("utf-8")
            result_s3_key = f"{results_folder}/{task_id}/result.json"

            await asyncio.to_thread(
                lambda: s3_client.put_object(
                    Bucket=s3_bucket,
                    Key=result_s3_key,
                    Body=result_json_bytes,
                    ContentType="application/json",
                    Metadata={"task_id": task_id, "engine_type": self.engine_type},
                )
            )
            self.logger.info(
                '{"event": "json_saved", "taskId": "%s", "s3Key": "%s", "sizeBytes": %d}',
                task_id, result_s3_key, len(result_json_bytes),
            )
            result_upload_ms = _elapsed_ms(t_phase)

        return {
            "message_type": "worker_completion",
            "task_id": task_id,
            "task_db_id": task_db_id,
            "status": "completed",
            "result_json_s3_key": result_s3_key,
            "metadata": {
                **metadata,
                "model_load_time_ms": model_load_time_ms,
                "processing_time_ms": processing_time_ms,
                "analysis_time_ms": analysis_time_ms,
                "law_pack_download_ms": law_pack_download_ms,
                "input_download_ms": input_download_ms,
                "result_upload_ms": result_upload_ms,
                "engine_job_ms": _elapsed_ms(t_start),
                "pdf_generation": PDF_GENERATION_MODE,
                "engine_type": self.engine_type,
                "sdk_version": SDK_VERSION,
            },
        }

    # ── Main run loop ─────────────────────────────────────────────────────────

    async def run(self, sdk: Any) -> None:
        """
        Validate model cache, load models via sdk.on_startup(), then poll SQS forever.
        Blocks until the process is killed (normal ECS behaviour).

        Args:
            sdk: An instantiated engine SDK object (LawEngineSDK, ISO9001EngineSDK,
                 StandardEngineSDK, …) that exposes on_startup(),
                 process_query(), and process_file(). Implementations should load every
                 model or library used by those handlers inside on_startup so the
                 ``worker_ready`` log line reflects a fully warm worker.
        """
        model_dir: str = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/app/models")
        queue_url: Optional[str] = os.environ.get(self.queue_env_var)
        backend_queue_url: Optional[str] = os.environ.get("SQS_TASK_QUEUE_URL")
        s3_bucket: Optional[str] = os.environ.get("S3_BUCKET_NAME")
        aws_region: str = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        results_folder: str = os.environ.get("S3_RESULTS_FOLDER", "results")
        visibility_timeout: int = int(os.environ.get("SQS_VISIBILITY_TIMEOUT", "300"))

        missing = [
            name for name, val in [
                (self.queue_env_var, queue_url),
                ("SQS_TASK_QUEUE_URL", backend_queue_url),
                ("S3_BUCKET_NAME", s3_bucket),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                f"Required environment variables not set: {', '.join(missing)}"
            )

        self.logger.info(
            '{"event": "worker_starting", "engineType": "%s"}', self.engine_type
        )

        # ── Step 1: validate model cache directory ────────────────────────────
        self._validate_model_directory(model_dir)

        # ── Step 2: load models from local cache (once) ───────────────────────
        self.logger.info(
            '{"event": "loading_models", "modelDir": "%s"}', model_dir
        )
        t_load = time.monotonic()
        await sdk.on_startup()
        model_load_time_ms = int((time.monotonic() - t_load) * 1000)
        self.logger.info(
            '{"event": "models_loaded", "modelDir": "%s", "modelLoadTimeMs": %d}',
            model_dir, model_load_time_ms,
        )

        # ── Step 3: AWS clients ───────────────────────────────────────────────
        sqs = boto3.client("sqs", region_name=aws_region)
        s3 = boto3.client("s3", region_name=aws_region)

        self.logger.info(
            '{"event": "worker_ready", "engineType": "%s", "queueUrl": "%s"}',
            self.engine_type, queue_url,
        )

        # ── Step 4: poll SQS ──────────────────────────────────────────────────
        while True:
            try:
                response = await asyncio.to_thread(
                    sqs.receive_message,
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=20,
                    VisibilityTimeout=visibility_timeout,
                    MessageAttributeNames=["All"],
                )

                for message in response.get("Messages", []):
                    receipt_handle: str = message["ReceiptHandle"]
                    message_id: str = message["MessageId"]

                    try:
                        body: Dict[str, Any] = json.loads(message["Body"])
                    except json.JSONDecodeError as e:
                        self.logger.error(
                            '{"event": "invalid_message", "messageId": "%s", "error": "%s"}',
                            message_id, str(e),
                        )
                        await asyncio.to_thread(
                            sqs.delete_message,
                            QueueUrl=queue_url,
                            ReceiptHandle=receipt_handle,
                        )
                        continue

                    task_id: str = body.get("task_id", "?")
                    self.logger.info(
                        '{"event": "job_received", "taskId": "%s", "messageId": "%s"}',
                        task_id, message_id,
                    )

                    try:
                        completion = await self._process_job(
                            sdk, body, sqs, backend_queue_url, s3, s3_bucket, results_folder,
                            model_load_time_ms,
                        )

                        # Notify backend before deleting so the job is never lost.
                        await asyncio.to_thread(
                            sqs.send_message,
                            QueueUrl=backend_queue_url,
                            MessageBody=json.dumps(completion, default=str),
                        )
                        await asyncio.to_thread(
                            sqs.delete_message,
                            QueueUrl=queue_url,
                            ReceiptHandle=receipt_handle,
                        )

                        self.logger.info(
                            '{"event": "job_completed", "taskId": "%s", "messageId": "%s", '
                            '"processingTimeMs": %d, "analysisTimeMs": %d, "engineJobMs": %d, '
                            '"modelLoadTimeMs": %d}',
                            task_id, message_id,
                            completion["metadata"]["processing_time_ms"],
                            completion["metadata"]["analysis_time_ms"],
                            completion["metadata"]["engine_job_ms"],
                            model_load_time_ms,
                        )

                    except Exception as exc:
                        self.logger.error(
                            '{"event": "job_failed", "taskId": "%s", "messageId": "%s", '
                            '"error": "%s"}',
                            task_id, message_id,
                            str(exc).replace('"', "'"),
                            exc_info=True,
                        )
                        # Tell the backend to mark the task as failed in the DB.
                        try:
                            await asyncio.to_thread(
                                sqs.send_message,
                                QueueUrl=backend_queue_url,
                                MessageBody=json.dumps({
                                    "message_type": "worker_completion",
                                    "task_id": task_id,
                                    "task_db_id": body.get("task_db_id"),
                                    "status": "failed",
                                    "error": str(exc),
                                }),
                            )
                        except Exception as notify_err:
                            self.logger.error(
                                '{"event": "failure_notify_error", "taskId": "%s", '
                                '"error": "%s"}',
                                task_id, str(notify_err),
                            )
                        # Do NOT delete — let SQS visibility timeout expire for retry / DLQ.

            except Exception as outer_exc:
                self.logger.error(
                    '{"event": "poll_error", "error": "%s"}',
                    str(outer_exc).replace('"', "'"),
                    exc_info=True,
                )
                await asyncio.sleep(5)
