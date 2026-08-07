import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Callable, Any
import logging

from wcrond.job import CronJob
from wcrond.state import StateStore

logger = logging.getLogger(__name__)

class RetryManager:
    def __init__(self, state_store: StateStore, execution_callback: Callable[[CronJob, str, int], Any]):
        self.state_store = state_store
        self.execution_callback = execution_callback
        self.timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def schedule_retry(self, job: CronJob, attempt: int, reason: str = ""):
        if attempt > job.retry.max_retries + 1: # attempt is 1-indexed, retries count max_retries additional executions
            logger.info(f"Max retries reached for job {job.job_id}")
            return

        delay = min(
            job.retry.initial_delay_s * (job.retry.backoff_multiplier ** (attempt - 2)),
            job.retry.max_delay_s
        )
        
        next_retry_at = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()
        
        self.state_store.add_retry(job.job_id, attempt, next_retry_at, reason)
        
        with self._lock:
            if job.job_id in self.timers:
                self.timers[job.job_id].cancel()
            
            timer = threading.Timer(delay, self._execute_retry, args=[job, attempt])
            self.timers[job.job_id] = timer
            timer.start()
        
        logger.info(f"Scheduled retry {attempt-1}/{job.retry.max_retries} for job {job.job_id} in {delay}s")

    def _execute_retry(self, job: CronJob, attempt: int):
        with self._lock:
            self.timers.pop(job.job_id, None)
        self.state_store.remove_retry(job.job_id)
        self.execution_callback(job, "retry", attempt)

    def cancel_retry(self, job_id: str):
        with self._lock:
            timer = self.timers.pop(job_id, None)
            if timer:
                timer.cancel()
        self.state_store.remove_retry(job_id)
        logger.info(f"Cancelled retry for job {job_id}")

    def cancel_all(self):
        with self._lock:
            for job_id, timer in self.timers.items():
                timer.cancel()
            self.timers.clear()
            
    def get_pending_retries(self):
        return self.state_store.get_retry_queue()
