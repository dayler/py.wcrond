import threading
import time
import logging
from datetime import datetime, timezone
import psutil

from wcrond.state import StateStore
from wcrond.config import WcrondConfig

logger = logging.getLogger(__name__)

class Watchdog:
    def __init__(self, state_store: StateStore, config: WcrondConfig):
        self.state_store = state_store
        self.config = config
        self._stop_event = threading.Event()
        self._thread = None
        self.grace_period = self.config.grace_period if hasattr(self.config, 'grace_period') else 16
        self._last_cleanup = 0.0

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True, name="WatchdogThread")
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.monitor_running_jobs()
                self._maybe_cleanup()
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
            self._stop_event.wait(self.config.watchdog_check_interval if hasattr(self.config, 'watchdog_check_interval') else 30)

    def monitor_running_jobs(self):
        zombies = self.detect_zombies()
        for zombie in zombies:
            if hasattr(self.config, 'watchdog_auto_kill_zombies') and getattr(self.config, 'watchdog_auto_kill_zombies', True):
                self.kill_zombie(zombie)

    def detect_zombies(self) -> list:
        zombies = []
        running_jobs = self.state_store.get_running_jobs()
        now = datetime.now(timezone.utc)
        default_timeout = self.config.default_timeout if hasattr(self.config, 'default_timeout') else 3600
        
        for job_state in running_jobs:
            if not job_state.start_time:
                continue
            
            start_dt = datetime.fromisoformat(job_state.start_time)
            duration_s = (now - start_dt).total_seconds()
            
            if duration_s > default_timeout * 2:  # Safe heuristic for now
                if job_state.pid and psutil.pid_exists(job_state.pid):
                    zombies.append(job_state)
                else:
                    # Process died, but state not updated
                    self.state_store.record_end(job_state.execution_id, -1, "TIMEOUT", "", "Process died")
        return zombies

    def _maybe_cleanup(self):
        now = time.time()
        interval_s = self.config.cleanup_interval_hours * 3600
        if now - self._last_cleanup >= interval_s:
            try:
                self.state_store.cleanup_old_records(self.config.history_retention_days)
                logger.info(f"Cleaned up records older than {self.config.history_retention_days} days")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            self._last_cleanup = now

    def kill_zombie(self, job_state):
        if not job_state.pid:
            return
        
        logger.warning(f"ZOMBIE_DETECTED: Killing execution {job_state.execution_id} (PID {job_state.pid})")
        
        try:
            p = psutil.Process(job_state.pid)
            p.terminate()
            try:
                p.wait(timeout=self.grace_period)
            except psutil.TimeoutExpired:
                p.kill()
        except psutil.NoSuchProcess:
            pass
        except Exception as e:
            logger.error(f"Failed to kill zombie {job_state.pid}: {e}")
            
        self.state_store.record_end(job_state.execution_id, -9, "TIMEOUT", "", "Killed by watchdog")
