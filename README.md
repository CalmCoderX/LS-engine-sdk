# LexaShield Engine SDK

SDK for building LexaShield processing engines. Engines run as ECS/Fargate SQS workers — each container loads ML models from EFS once into memory and processes many jobs without reloading.

---

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -e .
```

---

## How it works

Each engine container:

1. Validates that the EFS model directory exists and is non-empty.
2. Calls `on_startup()` to load ML models from EFS into memory (once per container lifetime).
3. Polls an engine-specific SQS queue continuously.
4. For each job: runs inference with the already-loaded models, saves the result JSON to S3, sends a `worker_completion` message to the backend queue, then deletes the engine queue message.
5. On failure: notifies the backend but does **not** delete the message — SQS retries / DLQ handles it.

Engines do not generate PDF reports. The backend generates them from `results/{task_id}/result.json` on download.

### Timing metrics

Each `worker_completion` includes timings in `metadata` (milliseconds), reported by `GET /api/pa/engines/performance`.

| Field | Meaning |
|---|---|
| `processing_time_ms` | Law pack download + analysis |
| `analysis_time_ms` | `process_query` / `process_file` only |
| `law_pack_download_ms` | Law pack JSONL downloads from S3 |
| `input_download_ms` | Input document download from S3 (file jobs, else 0) |
| `result_upload_ms` | Report metadata enrichment + JSON serialisation + S3 upload |
| `engine_job_ms` | Whole job, from message pick-up to completion being ready |
| `model_load_time_ms` | One-off model load at container start |
| `pdf_generation` | Always `"on_demand"` |
| `sdk_version` | SDK version that ran the job |

---

## Minimal example

### worker.py (entry point)

```python
import asyncio, os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)

from engine import MyEngineSDK
from lexashield_engine import SQSWorker

if __name__ == "__main__":
    sdk = MyEngineSDK()
    worker = SQSWorker(engine_type="law", queue_env_var="SQS_LAW_QUEUE_URL")
    asyncio.run(worker.run(sdk))
```

### Engine class

```python
from lexashield_engine import BaseEngine, ProcessingContext

class MyEngineSDK(BaseEngine):

    async def on_startup(self):
        """Load ML models from EFS into memory — called once on container start."""
        self.model = load_my_model(os.environ["SENTENCE_TRANSFORMERS_HOME"])

    async def process_query(self, ctx: ProcessingContext, query: str) -> tuple:
        await ctx.update_progress(50, "Analyzing...")
        results = self.model.encode(query)
        return [{"results": results}], {"input_type": "query"}

    async def process_file(self, ctx: ProcessingContext, file_path: str) -> tuple:
        await ctx.update_progress(30, "Reading file...")
        with open(file_path) as f:
            content = f.read()
        results = self.model.encode(content)
        return [{"results": results}], {"input_type": "file"}
```

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SENTENCE_TRANSFORMERS_HOME` | Yes | `/mnt/models` | EFS model directory (local cache for dev) |
| `HF_HOME` | Yes | `/mnt/models` | HuggingFace cache dir — set same as above |
| `TRANSFORMERS_CACHE` | Yes | `/mnt/models` | Transformers cache dir — set same as above |
| `SQS_<ENGINE>_QUEUE_URL` | Yes | — | Engine-specific SQS queue URL |
| `SQS_TASK_QUEUE_URL` | Yes | — | Backend completion queue URL |
| `S3_BUCKET_NAME` | Yes | — | S3 bucket for result storage |
| `S3_RESULTS_FOLDER` | No | `results` | S3 key prefix for results |
| `SQS_VISIBILITY_TIMEOUT` | No | `300` | Seconds to hide a message during processing |
| `AWS_DEFAULT_REGION` | No | `us-east-1` | AWS region |
| `LOG_LEVEL` | No | `INFO` | Logging level |

Set these in the engine's `.env` for local development. In production they come from the ECS task definition.

---

## ProcessingContext

Passed to `process_query` and `process_file` by the worker.

| Attribute / Method | Description |
|---|---|
| `ctx.task_id` | Unique task identifier |
| `ctx.law_pack_file_paths` | `List[Path]` — downloaded law pack JSONL files |
| `ctx.title` | Report/document title from the platform |
| `ctx.elapsed_seconds` | Seconds since processing started |
| `await ctx.update_progress(percent, message)` | Logs progress to stdout |

---

## SQSWorker reference

```python
SQSWorker(
    engine_type: str,       # 'law' | 'iso' | 'standard' — used in logs
    queue_env_var: str,     # name of the env var holding the engine queue URL
    logger_name: str = None
)

await worker.run(sdk)       # blocks forever — ECS restarts the container on exit
```

---

## Local development

Download all ML models to a local directory before running an engine locally:

```bash
python scripts/seed_local_models.py

# Target a specific directory:
python scripts/seed_local_models.py --dir C:\Users\you\.cache\lexa-models

# Single engine only:
python scripts/seed_local_models.py --engines law
```

Then set `SENTENCE_TRANSFORMERS_HOME`, `HF_HOME`, and `TRANSFORMERS_CACHE` in the engine's `.env` to that directory.
