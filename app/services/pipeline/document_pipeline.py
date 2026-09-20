"""Document pipeline for CivicOS.

Handles incoming document triage requests and enqueues them for processing.
"""

from typing import Dict, Any
from app.services.workers.background import BackgroundTaskWorker


class DocumentPipeline:
    """Pipeline for processing document triage requests."""

    def __init__(self):
        """Initialize the document pipeline."""
        self.worker = BackgroundTaskWorker()

    async def process_triage_request(self, request_data: Dict[str, Any]) -> str:
        """Process an incoming document triage request.

        Args:
            request_data: Document data and processing instructions

        Returns:
            Task ID of the enqueued work
        """
        task_id = await self.worker.enqueue_task(request_data)
        return task_id
