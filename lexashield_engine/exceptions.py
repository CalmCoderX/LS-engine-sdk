"""Custom exceptions for LexaShield Engine SDK"""


class EngineError(Exception):
    """Base exception for all engine errors"""
    pass


class ProcessingError(EngineError):
    """Error during task processing"""
    
    def __init__(self, message: str, task_id: str = None):
        super().__init__(message)
        self.task_id = task_id


class BackendConnectionError(EngineError):
    """Error connecting to LexaShield backend"""
    pass


class LawPackNotFoundError(EngineError):
    """Requested law pack not found"""
    
    def __init__(self, law_pack_id: int):
        super().__init__(f"Law pack {law_pack_id} not found")
        self.law_pack_id = law_pack_id


class WebhookError(BackendConnectionError):
    """Error sending webhook to backend"""
    
    def __init__(self, message: str, webhook_type: str = None):
        super().__init__(message)
        self.webhook_type = webhook_type
