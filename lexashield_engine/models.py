"""Pydantic models for LexaShield Engine SDK"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ProcessingRequest(BaseModel):
    """Request from backend to process a task"""
    task_id: str = Field(..., description="Unique task identifier")
    library: str = Field(..., description="Law pack ID to use (as string)")
    query: Optional[str] = Field(None, description="Text query to process")
    library_name: Optional[str] = Field(None, description="Law pack display name(s) from the platform")
    library_version: Optional[str] = Field(None, description="Law pack version(s) from the platform database")
    engine_name: Optional[str] = Field(None, description="Registered engine name from the platform")
    engine_version: Optional[str] = Field(None, description="Engine version stored on the platform (e.g. from health check)")
    
    @property
    def law_pack_id(self) -> int:
        """Get law pack ID as integer"""
        return int(self.library)


class ProgressUpdate(BaseModel):
    """Progress update to send to backend"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Current status (processing, completed, failed)")
    percent: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(None, description="Optional status message")


class CompletionResult(BaseModel):
    """Completion notification to send to backend"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(..., description="Final status (completed or failed)")
    result_json_url: Optional[str] = Field(None, description="URL to download JSON result")
    result_html_url: Optional[str] = Field(None, description="URL to download HTML result")
    result_pdf_url: Optional[str] = Field(None, description="URL to download PDF result")
    result_excel_url: Optional[str] = Field(None, description="URL to download Excel result")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing metadata")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy", description="Health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    version: str = Field(default="1.0.0", description="Engine version")
    uptime_seconds: Optional[float] = Field(None, description="Uptime in seconds")


class ProcessingResponse(BaseModel):
    """Response when accepting a processing request"""
    task_id: str = Field(..., description="Task identifier")
    status: str = Field(default="accepted", description="Request status")
    message: str = Field(default="Processing request accepted")
