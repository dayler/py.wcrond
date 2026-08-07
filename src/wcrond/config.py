import os
from pathlib import Path
from dataclasses import dataclass, field
import tomllib
from wcrond.job import RetryConfig

@dataclass
class WcrondConfig:
    pool_size: int = 4
    tick_interval_s: float = 1.0
    log_dir: str = "logs"
    db_path: str = "data/wcrond.db"
    pid_file: str = "data/wcrond.pid"
    ipc_pipe_name: str = "\\\\.\\pipe\\wcrond"
    default_shell: str = "powershell"
    default_timeout: int = 3600
    default_retry: RetryConfig = field(default_factory=RetryConfig)
    history_retention_days: int = 30
    default_working_dir: str = "%USERPROFILE%"
    grace_period: int = 16
    log_level: str = "INFO"
    log_max_bytes: int = 10_485_760
    log_backup_count: int = 5
    capture_job_output: bool = True
    output_tail_lines: int = 100
    cleanup_interval_hours: int = 24
    ipc_client_timeout: int = 5
    watchdog_check_interval: int = 30
    watchdog_auto_kill_zombies: bool = True

    base_dir: Path = field(default_factory=lambda: Path(os.environ.get("USERPROFILE", "~")).expanduser() / ".wcrond")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "WcrondConfig":
        if path is None:
            base_dir = Path(os.environ.get("USERPROFILE", "~")).expanduser() / ".wcrond"
            path = base_dir / "wcrond.toml"
        else:
            path = Path(path)
            base_dir = path.parent

        if not path.exists():
            return cls(base_dir=base_dir)

        with open(path, "rb") as f:
            data = tomllib.load(f)

        config = cls(base_dir=base_dir)
        
        daemon = data.get("daemon", {})
        config.tick_interval_s = float(daemon.get("tick_interval", config.tick_interval_s))
        config.pid_file = str(daemon.get("pid_file", config.pid_file))
        config.default_shell = str(daemon.get("default_shell", config.default_shell))
        config.default_working_dir = str(daemon.get("default_working_dir", config.default_working_dir))

        pool = data.get("pool", {})
        config.pool_size = int(pool.get("max_workers", config.pool_size))
        config.default_timeout = int(pool.get("default_timeout", config.default_timeout))
        config.grace_period = int(pool.get("grace_period", config.grace_period))

        retry = data.get("retry", {})
        config.default_retry = RetryConfig(
            max_retries=int(retry.get("max_retries", config.default_retry.max_retries)),
            initial_delay_s=int(retry.get("initial_delay_s", config.default_retry.initial_delay_s)),
            backoff_multiplier=float(retry.get("backoff_multiplier", config.default_retry.backoff_multiplier)),
            max_delay_s=int(retry.get("max_delay_s", config.default_retry.max_delay_s)),
        )

        logging = data.get("logging", {})
        config.log_dir = str(logging.get("log_dir", config.log_dir))
        config.log_level = str(logging.get("level", config.log_level))
        config.log_max_bytes = int(logging.get("max_bytes", config.log_max_bytes))
        config.log_backup_count = int(logging.get("backup_count", config.log_backup_count))
        config.capture_job_output = bool(logging.get("capture_job_output", config.capture_job_output))
        config.output_tail_lines = int(logging.get("output_tail_lines", config.output_tail_lines))

        database = data.get("database", {})
        config.db_path = str(database.get("path", config.db_path))
        config.history_retention_days = int(database.get("history_retention_days", config.history_retention_days))
        config.cleanup_interval_hours = int(database.get("cleanup_interval_hours", config.cleanup_interval_hours))

        ipc = data.get("ipc", {})
        config.ipc_pipe_name = str(ipc.get("pipe_name", config.ipc_pipe_name))
        config.ipc_client_timeout = int(ipc.get("client_timeout", config.ipc_client_timeout))

        watchdog = data.get("watchdog", {})
        config.watchdog_check_interval = int(watchdog.get("check_interval", config.watchdog_check_interval))
        config.watchdog_auto_kill_zombies = bool(watchdog.get("auto_kill_zombies", config.watchdog_auto_kill_zombies))

        return config

    def get_absolute_path(self, rel_path: str) -> Path:
        p = Path(rel_path)
        if p.is_absolute():
            return p
        return (self.base_dir / p).resolve()
