"""
LexaShield Engine SDK

SDK for building LexaShield processing engines.
Engines produce the analysis JSON; the backend generates PDF reports.
"""

from ._version import __version__

from .server import BaseEngine, ProcessingContext
from .connector import AsyncBackendConnector
from .models import (
    ProcessingRequest,
    ProgressUpdate,
    CompletionResult,
    HealthResponse,
)
from .config import EngineConfig
from .exceptions import (
    EngineError,
    ProcessingError,
    BackendConnectionError,
)
from .sqs_worker import SQSWorker

__all__ = [
    # Main classes
    "BaseEngine",
    "ProcessingContext",
    "AsyncBackendConnector",

    # SQS worker (ECS/Fargate)
    "SQSWorker",

    # Models
    "ProcessingRequest",
    "ProgressUpdate",
    "CompletionResult",
    "HealthResponse",

    # Config
    "EngineConfig",

    # Exceptions
    "EngineError",
    "ProcessingError",
    "BackendConnectionError",
]
