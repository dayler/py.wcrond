import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
import croniter

from wcrond.job import CronJob
from wcrond.state import StateStore

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self.jobs: Dict[str, CronJob] = {}
        self.last_minute: Optional[int] = None
        self._executor = None  # Will be set later (MS-05)
        self.running = False

    def set_executor(self, executor):
        self._executor = executor

    def add_job(self, job: CronJob):
        self.jobs[job.job_id] = job

    def run_reboot_jobs(self):
        for job in self.jobs.values():
            if job.schedule == "@reboot" and job.enabled:
                logger.info(f"Running @reboot job: {job.job_id}")
                self._submit(job, trigger="reboot")

    def tick(self, now: Optional[datetime] = None):
        """Called every tick_interval_s."""
        if now is None:
            now = datetime.now().astimezone()
            
        current_minute = now.replace(second=0, microsecond=0)
        current_minute_ts = int(current_minute.timestamp())

        if self.last_minute != current_minute_ts:
            self.last_minute = current_minute_ts
            self.evaluate_jobs(current_minute)

    def evaluate_jobs(self, current_minute: datetime):
        for job in self.jobs.values():
            if job.schedule == "@reboot":
                continue

            if not job.enabled:
                continue

            if croniter.croniter.match(job.schedule, current_minute):
                self._submit(job, trigger="scheduled")

    def _submit(self, job: CronJob, trigger: str):
        if job.overlap_policy == "skip":
            running = [e for e in self.state_store.get_running_jobs() if e.job_id == job.job_id]
            if running:
                logger.info(f"Skipping job {job.job_id} (overlap_policy=skip, already running)")
                return
        elif job.overlap_policy == "kill_previous":
            running = [e for e in self.state_store.get_running_jobs() if e.job_id == job.job_id]
            for r in running:
                logger.info(f"Killing previous instance of {job.job_id} ({r.execution_id})")
                if self._executor:
                    self._executor.kill(r.execution_id)
        
        logger.info(f"Submitting job {job.job_id} (trigger={trigger})")
        if self._executor:
            self._executor.submit_job(job, trigger=trigger)

    def force_run(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        self._submit(job, trigger="manual")

    def disable_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        job.enabled = False

    def enable_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        job.enabled = True

    def get_next_runs(self, job_id: str, n: int = 5) -> List[datetime]:
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")
        
        if job.schedule == "@reboot":
            return []

        now = datetime.now().astimezone()
        cron = croniter.croniter(job.schedule, now)
        return [cron.get_next(datetime) for _ in range(n)]
