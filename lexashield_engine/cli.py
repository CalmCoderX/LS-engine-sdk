"""CLI tool for scaffolding new LexaShield engine projects."""

import sys
import argparse
from pathlib import Path


ENGINE_TEMPLATE = '''"""
{class_name} — LexaShield Processing Engine
"""

import os
from lexashield_engine import BaseEngine, ProcessingContext


class {class_name}(BaseEngine):

    async def on_startup(self) -> None:
        """Load ML models from EFS into memory (called once on container start)."""
        model_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/mnt/models")
        # TODO: load your SentenceTransformer / ML models here
        # e.g. self.model = SentenceTransformer(model_id)

    async def process_query(self, ctx: ProcessingContext, query: str) -> tuple:
        """
        Process a text query.

        Args:
            ctx:   ProcessingContext — provides task_id, law_pack_file_paths, title,
                   elapsed_seconds, and update_progress().
            query: The text to analyse.

        Returns:
            (results, metadata) where results is a list containing the output dict
            and metadata is a plain dict of processing stats.
        """
        await ctx.update_progress(10, "Starting analysis...")

        # TODO: run your inference here using self.model and ctx.law_pack_file_paths
        result = {{"query": query, "flags": []}}

        await ctx.update_progress(100, "Complete")
        return [result], {{"input_type": "query"}}

    async def process_file(self, ctx: ProcessingContext, file_path: str) -> tuple:
        """
        Process an uploaded file.

        Args:
            ctx:       ProcessingContext
            file_path: Local path to the downloaded input file.

        Returns:
            (results, metadata)
        """
        await ctx.update_progress(10, "Reading file...")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # TODO: run your inference here
        result = {{"file_size": len(content), "flags": []}}

        await ctx.update_progress(100, "Complete")
        return [result], {{"input_type": "file"}}
'''


WORKER_TEMPLATE = '''"""
{engine_name} worker entry point — ECS/Fargate SQS worker.
"""

import asyncio
import os

# Load .env for local dev. override=False so ECS task definition vars always win.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=False)
except ImportError:
    pass

# Must be set before any model library is imported.
_MODEL_DIR = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "/mnt/models")
os.environ["SENTENCE_TRANSFORMERS_HOME"] = _MODEL_DIR
os.environ.setdefault("HF_HOME", _MODEL_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", _MODEL_DIR)

import logging  # noqa: E402
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from {module_name} import {class_name}
from lexashield_engine import SQSWorker

if __name__ == "__main__":
    sdk = {class_name}()
    worker = SQSWorker(engine_type="{engine_name}", queue_env_var="SQS_{env_prefix}_QUEUE_URL")
    asyncio.run(worker.run(sdk))
'''


ENV_TEMPLATE = '''# {engine_name} Worker — local development
# Gitignored. In production, env vars come from the ECS task definition.

# ── AWS credentials ───────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=us-east-1

# ── SQS queues ────────────────────────────────────────────────────────────────
SQS_{env_prefix}_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/{queue_name}
SQS_TASK_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/YOUR_ACCOUNT_ID/lexa-backend-tasks

# ── S3 storage ────────────────────────────────────────────────────────────────
S3_BUCKET_NAME=your-lexa-bucket
S3_RESULTS_FOLDER=results

# ── Model storage (run scripts/seed_local_models.py once to populate) ─────────
SENTENCE_TRANSFORMERS_HOME=/mnt/models
HF_HOME=/mnt/models
TRANSFORMERS_CACHE=/mnt/models

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
'''


DOCKERFILE_TEMPLATE = '''FROM python:3.11-slim

LABEL org.opencontainers.image.title="{engine_name}-worker"

WORKDIR /app

RUN apt-get update \\
    && apt-get install -y --no-install-recommends gcc g++ \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# /mnt/models is mounted from EFS at runtime.
ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1

CMD ["python", "worker.py"]
'''

REQUIREMENTS_TEMPLATE = '''# PyTorch CPU-only (avoids downloading ~1.5 GB CUDA packages)
--extra-index-url https://download.pytorch.org/whl/cpu

git+https://github.com/perfectopdev/lexashield-engine-sdk.git@2.0.1
numpy
torch>=2.6.0
sentence_transformers
nltk
cryptography
boto3==1.43.2
python-dotenv==1.2.2
'''


def create_engine(name: str, directory: Path) -> int:
    """Scaffold a new SQS worker engine project."""
    engine_dir = directory / name
    if engine_dir.exists():
        print(f"Error: Directory {engine_dir} already exists")
        return 1

    engine_dir.mkdir(parents=True)

    module_name = name.replace("-", "_")
    class_name = "".join(word.capitalize() for word in name.split("-"))
    env_prefix = name.replace("-", "_").upper()
    queue_name = f"lexa-{name}"

    # engine class
    (engine_dir / f"{module_name}.py").write_text(
        ENGINE_TEMPLATE.format(class_name=class_name)
    )

    # worker entry point
    (engine_dir / "worker.py").write_text(
        WORKER_TEMPLATE.format(
            engine_name=name,
            module_name=module_name,
            class_name=class_name,
            env_prefix=env_prefix,
        )
    )

    # .env (local dev, gitignored)
    (engine_dir / ".env").write_text(
        ENV_TEMPLATE.format(
            engine_name=name,
            env_prefix=env_prefix,
            queue_name=queue_name,
        )
    )

    # Dockerfile
    (engine_dir / "Dockerfile").write_text(
        DOCKERFILE_TEMPLATE.format(engine_name=name)
    )

    # requirements.txt
    (engine_dir / "requirements.txt").write_text(REQUIREMENTS_TEMPLATE)

    # .gitignore
    (engine_dir / ".gitignore").write_text(
        "venv/\n__pycache__/\n.env\n*.pyc\nlogs/\nresults/\n"
    )

    # .dockerignore
    (engine_dir / ".dockerignore").write_text(
        "venv/\n.env\n.env.*\n__pycache__/\n*.pyc\nlogs/\nresults/\n.git/\n.gitignore\n"
    )

    print(f"\nCreated engine: {engine_dir}")
    print(f"\nFiles created:")
    print(f"   {module_name}.py  — implement on_startup(), process_query(), process_file()")
    print(f"   worker.py        — ECS/Fargate entry point (do not modify)")
    print(f"   .env             — fill in AWS credentials and queue URLs for local dev")
    print(f"   Dockerfile       — ECS container definition")
    print(f"   requirements.txt — Python dependencies")
    print(f"\nNext steps:")
    print(f"   1. cd {engine_dir}")
    print(f"   2. Edit {module_name}.py to implement your ML logic")
    print(f"   3. Fill in .env with your local AWS credentials and queue URLs")
    print(f"   4. python scripts/seed_local_models.py  (download models once)")
    print(f"   5. python worker.py  (run locally)")
    print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LexaShield Engine SDK CLI",
        prog="lexashield-engine",
    )
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser("create", help="Scaffold a new engine project")
    create_parser.add_argument("name", type=str, help="Engine name, e.g. my-legal-engine")
    create_parser.add_argument(
        "--dir", type=str, default=".", help="Parent directory (default: current)"
    )

    subparsers.add_parser("version", help="Show SDK version")

    args = parser.parse_args()

    if args.command == "create":
        return create_engine(args.name, Path(args.dir).resolve())
    elif args.command == "version":
        from lexashield_engine import __version__
        print(f"lexashield-engine-sdk {__version__}")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
