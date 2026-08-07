import tomllib
from pathlib import Path
from typing import Dict
import croniter
from wcrond.job import CronJob, RetryConfig
from wcrond.config import WcrondConfig

SHORTCUTS = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

class WcrontabParser:
    def __init__(self, config: WcrondConfig):
        self.config = config

    def parse_all(self) -> Dict[str, CronJob]:
        jobs = {}
        
        main_wcrontab = self.config.get_absolute_path("wcrontab.toml")
        if main_wcrontab.exists():
            jobs.update(self._parse_file(main_wcrontab))

        jobs_d = self.config.get_absolute_path("jobs.d")
        if jobs_d.exists() and jobs_d.is_dir():
            for file_path in jobs_d.glob("*.toml"):
                file_jobs = self._parse_file(file_path)
                for job_id, job in file_jobs.items():
                    if job_id in jobs:
                        raise ValueError(f"Duplicate job_id found: {job_id} in {file_path.name}")
                    jobs[job_id] = job
                    
        return jobs

    def _parse_file(self, path: Path) -> Dict[str, CronJob]:
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Error parsing {path}: {e}")

        jobs = {}
        jobs_data = data.get("jobs", {})
        
        for job_id, job_dict in jobs_data.items():
            if "schedule" not in job_dict:
                raise ValueError(f"Job {job_id} missing 'schedule' field")
            if "command" not in job_dict:
                raise ValueError(f"Job {job_id} missing 'command' field")

            schedule = str(job_dict["schedule"])
            if schedule.lower() in SHORTCUTS:
                schedule = SHORTCUTS[schedule.lower()]
            
            if schedule != "@reboot" and not croniter.croniter.is_valid(schedule):
                raise ValueError(f"Invalid cron expression for job {job_id}: {schedule}")

            retry_data = job_dict.get("retry", {})
            retry_config = RetryConfig(
                max_retries=int(retry_data.get("max_retries", self.config.default_retry.max_retries)),
                initial_delay_s=int(retry_data.get("initial_delay_s", self.config.default_retry.initial_delay_s)),
                backoff_multiplier=float(retry_data.get("backoff_multiplier", self.config.default_retry.backoff_multiplier)),
                max_delay_s=int(retry_data.get("max_delay_s", self.config.default_retry.max_delay_s)),
            )
            
            job = CronJob(
                job_id=job_id,
                command=str(job_dict["command"]),
                schedule=schedule,
                name=job_dict.get("name", job_id),
                shell=job_dict.get("shell"),
                enabled=bool(job_dict.get("enabled", True)),
                timeout=job_dict.get("timeout", self.config.default_timeout),
                overlap_policy=str(job_dict.get("overlap_policy", "skip")),
                retry=retry_config,
                env={str(k): str(v) for k, v in job_dict.get("env", {}).items()},
                working_dir=job_dict.get("working_dir", self.config.default_working_dir),
                on_success=job_dict.get("on_success"),
                on_failure=job_dict.get("on_failure"),
            )
            jobs[job_id] = job
            
        return jobs
