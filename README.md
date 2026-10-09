# LexaShield Engine SDK

Base class and SQS worker for LexaShield analysis engines. Each engine runs as an ECS/Fargate container that loads its models once and processes jobs from its SQS queue.

## Installation

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -e .
```

## How it works

Each engine container:

1. Checks that the model directory exists and is not empty.
2. Calls `on_startup()` to load models into memory.
3. Polls its SQS queue.
4. For each job: downloads the law pack files, runs `process_query()` or `process_file()`, saves `results/{task_id}/result.json` to S3, sends `worker_completion` to the backend queue, then deletes the job message.
5. On failure: notifies the backend and leaves the message for SQS retry / DLQ.

The backend generates PDF reports from `result.json` on download.

### Timing metrics

`worker_completion` metadata includes these timings (milliseconds), reported by `GET /api/pa/engines/performance`.

| Field | Meaning |
|---|---|
| `analysis_time_ms` | `process_query` / `process_file` |
| `law_pack_download_ms` | Law pack downloads from S3 |
| `input_download_ms` | Input file download from S3 (file jobs, else 0) |
| `result_upload_ms` | Report metadata, JSON serialisation and S3 upload |
| `engine_job_ms` | Whole job, from message pick-up to completion |
| `model_load_time_ms` | Model load at container start |

It also includes `engine_type` and `sdk_version`.

## Minimal example

### worker.py

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
        self.model = load_my_model(os.environ["SENTENCE_TRANSFORMERS_HOME"])

    async def process_query(self, ctx: ProcessingContext, query: str) -> tuple:
        await ctx.update_progress(50, "Analyzing...")
        results = self.model.encode(query)
        return [{"results": results}], {"input_type": "query"}

    async def process_file(self, ctx: ProcessingContext, file_path: str) -> tuple:
        with open(file_path) as f:
            content = f.read()
        results = self.model.encode(content)
        return [{"results": results}], {"input_type": "file"}
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `SQS_<ENGINE>_QUEUE_URL` | Yes | — | Engine SQS queue URL |
| `SQS_TASK_QUEUE_URL` | Yes | — | Backend queue URL |
| `S3_BUCKET_NAME` | Yes | — | Result bucket |
| `SENTENCE_TRANSFORMERS_HOME` | No | `/app/models` | Model directory |
| `S3_RESULTS_FOLDER` | No | `results` | S3 key prefix for results |
| `SQS_VISIBILITY_TIMEOUT` | No | `300` | Seconds a job stays hidden while processing |
| `AWS_DEFAULT_REGION` | No | `us-east-1` | AWS region |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FILE` | No | `~/lexashield/logs/engine.log` | Log file |
| `LOG_TO_CONSOLE` | No | `true` | Also log to the console |

Use the engine's `.env` for local development. In production they come from the ECS task definition.

## ProcessingContext

| Attribute / Method | Description |
|---|---|
| `ctx.task_id` | Task ID |
| `ctx.law_pack_file_paths` | `List[Path]` of downloaded law pack files |
| `ctx.title` | Report title from the platform |
| `ctx.language` | Language selected on the platform |
| `ctx.elapsed_seconds` | Seconds since the job started |
| `await ctx.update_progress(percent, message)` | Logs progress and sends it to the backend |

## SQSWorker

```python
SQSWorker(
    engine_type: str,       # 'law' | 'iso' | 'standard'
    queue_env_var: str,     # env var holding the engine queue URL
    logger_name: str = None
)

await worker.run(sdk)       # runs until the container stops
```
