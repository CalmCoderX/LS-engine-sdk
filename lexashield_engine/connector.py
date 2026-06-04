"""Backend connector for sending webhooks to LexaShield backend"""

import logging
import aiohttp
from typing import Dict, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .models import ProgressUpdate, CompletionResult
from .config import EngineConfig
from .exceptions import BackendConnectionError, WebhookError

logger = logging.getLogger(__name__)


class AsyncBackendConnector:
    """Async connector for sending webhooks to LexaShield backend"""
    
    def __init__(self, config: Optional[EngineConfig] = None):
        """
        Initialize the backend connector
        
        Args:
            config: Engine configuration (uses global config if not provided)
        """
        from .config import config as global_config
        self.config = config or global_config
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            "Content-Type": "application/json",
        }
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(BackendConnectionError),
    )
    async def _post_webhook(self, url: str, data: Dict[str, Any], webhook_type: str) -> Dict[str, Any]:
        """
        Send POST request to webhook endpoint with retry logic
        
        Args:
            url: Webhook URL
            data: Data to send
            webhook_type: Type of webhook (for logging)
            
        Returns:
            Response data
            
        Raises:
            WebhookError: If webhook fails after retries
        """
        await self._ensure_session()
        
        try:
            logger.debug(f"Sending {webhook_type} webhook to {url}: {data}")
            
            async with self._session.post(url, json=data, headers=self._get_headers()) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    logger.info(f"{webhook_type} webhook sent successfully for task {data.get('task_id')}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"{webhook_type} webhook failed: {response.status} - {error_text}")
                    raise BackendConnectionError(
                        f"Webhook failed with status {response.status}: {error_text}"
                    )
        
        except aiohttp.ClientError as e:
            logger.error(f"{webhook_type} webhook connection error: {str(e)}")
            raise BackendConnectionError(f"Connection error: {str(e)}")
        
        except Exception as e:
            logger.error(f"{webhook_type} webhook unexpected error: {str(e)}")
            raise WebhookError(f"Unexpected error: {str(e)}", webhook_type=webhook_type)
    
    async def send_progress_update(
        self,
        task_id: str,
        percent: int,
        status: str = "processing",
        message: Optional[str] = None
    ) -> bool:
        """
        Send progress update to backend
        
        Args:
            task_id: Task identifier
            percent: Progress percentage (0-100)
            status: Status string (default: "processing")
            message: Optional status message
            
        Returns:
            True if successful
        """
        try:
            progress = ProgressUpdate(
                task_id=task_id,
                status=status,
                percent=max(0, min(100, percent)),  # Clamp to 0-100
                message=message
            )
            
            await self._post_webhook(
                url=self.config.progress_webhook_url,
                data=progress.model_dump(exclude_none=True),
                webhook_type="progress"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send progress update for task {task_id}: {str(e)}")
            # Don't raise - progress updates are not critical
            return False
    
    async def send_completion(
        self,
        task_id: str,
        result_urls: Dict[str, str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send completion notification to backend
        
        Args:
            task_id: Task identifier
            result_urls: Dictionary with keys: html_url, pdf_url, excel_url
            metadata: Optional processing metadata
            
        Returns:
            True if successful
            
        Raises:
            WebhookError: If completion webhook fails
        """
        completion = CompletionResult(
            task_id=task_id,
            status="completed",
            result_html_url=result_urls.get("html_url"),
            result_json_url=result_urls.get("json_url"),
            result_pdf_url=result_urls.get("pdf_url"),
            result_excel_url=result_urls.get("excel_url"),
            metadata=metadata or {}
        )
        
        await self._post_webhook(
            url=self.config.completion_webhook_url,
            data=completion.model_dump(exclude_none=True),
            webhook_type="completion"
        )
        return True
    
    async def send_failure(
        self,
        task_id: str,
        error_message: str
    ) -> bool:
        """
        Send failure notification to backend
        
        Args:
            task_id: Task identifier
            error_message: Error description
            
        Returns:
            True if successful
        """
        try:
            completion = CompletionResult(
                task_id=task_id,
                status="failed",
                error_message=error_message
            )
            
            await self._post_webhook(
                url=self.config.completion_webhook_url,
                data=completion.model_dump(exclude_none=True),
                webhook_type="failure"
            )
            return True
        
        except Exception as e:
            logger.error(f"Failed to send failure notification for task {task_id}: {str(e)}")
            raise
