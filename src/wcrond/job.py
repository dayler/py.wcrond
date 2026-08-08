from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay_s: int = 30
    backoff_multiplier: float = 2.0
    max_delay_s: int = 300

@dataclass
class CronJob:
    job_id: str
    command: str
    schedule: str
    name: str = ""
    shell: Optional[str] = None
    enabled: bool = True
    timeout: Optional[int] = None
    overlap_policy: str = "skip"  # skip, allow, kill_previous
    retry: RetryConfig = field(default_factory=RetryConfig)
    env: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    silent: bool = True

    def __post_init__(self):
        if not self.name:
            self.name = self.job_id
        if self.overlap_policy not in ("skip", "allow", "kill_previous"):
            raise ValueError(f"Invalid overlap_policy: {self.overlap_policy}")
