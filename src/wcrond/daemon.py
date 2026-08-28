import os
import sys
import time
import signal
import logging
from pathlib import Path
import psutil

from wcrond.config import WcrondConfig
from wcrond.state import StateStore
from wcrond.executor import Executor
from wcrond.retry import RetryManager
from wcrond.watchdog import Watchdog
from wcrond.ipc import IPCServer
from wcrond.scheduler import Scheduler
from wcrond.parser import WcrontabParser

logger = logging.getLogger(__name__)

class WcrondDaemon:
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.config = None
        self.state_store = None
        self.executor = None
        self.retry_manager = None
        self.watchdog = None
        self.ipc = None
        self.scheduler = None
        self.running = False
        self.start_time = None
        
    def start(self):
        # 1. Load config
        self.config = WcrondConfig.load(self.config_path)
        
        # 2. PID file
        pid_file = self.config.get_absolute_path(self.config.pid_file)
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text().strip())
                if self._is_wcrond_process(old_pid):
                    logger.error(f"wcrond is already running with PID {old_pid}")
                    sys.exit(1)
                else:
                    logger.warning(f"Removing stale PID file (PID {old_pid} is not wcrond)")
            except (ValueError, OSError):
                logger.warning("Corrupt PID file found. Removing.")
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(os.getpid()))
        
        # 3. StateStore
        db_path = self.config.get_absolute_path(self.config.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_store = StateStore(str(db_path))
        
        # 4. Executor & RetryManager & Scheduler
        self.scheduler = Scheduler(self.state_store)
        self.executor = Executor(self.config, self.state_store)
        self.retry_manager = RetryManager(self.state_store, self.executor.submit_job)
        self.executor.retry_manager = self.retry_manager
        self.scheduler.set_executor(self.executor)
        
        # Load jobs
        self._load_jobs()
        
        # 5. Watchdog
        self.watchdog = Watchdog(self.state_store, self.config)
        self.watchdog.start()
        
        self.ipc = IPCServer(self.config.ipc_pipe_name)
        # Register daemon specific handlers
        self.ipc.handlers["stop"] = self._handle_ipc_stop
        self.ipc.handlers["reload"] = self._handle_ipc_reload
        self.ipc.handlers["list"] = self._handle_ipc_list
        self.ipc.handlers["history"] = self._handle_ipc_history
        self.ipc.handlers["run"] = self._handle_ipc_run
        self.ipc.handlers["status"] = self._handle_ipc_status
        self.ipc.handlers["retries"] = self._handle_ipc_retries
        self.ipc.handlers["kill"] = self._handle_ipc_kill
        self.ipc.handlers["cancel-retry"] = self._handle_ipc_cancel_retry
        self.ipc.handlers["cancel-all-retries"] = self._handle_ipc_cancel_all_retries
        self.ipc.handlers["disable"] = self._handle_ipc_disable
        self.ipc.handlers["enable"] = self._handle_ipc_enable
        self.ipc.handlers["zombies"] = self._handle_ipc_zombies
        self.ipc.handlers["logs"] = self._handle_ipc_logs
        self.ipc.handlers["validate"] = self._handle_ipc_validate
        self.ipc.handlers["next"] = self._handle_ipc_next
        self.ipc.start()
        
        # 7. Setup signals
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGBREAK, self._signal_handler)
        except AttributeError:
            pass
        
        self.running = True
        self.start_time = time.time()
        logger.info("wcrond daemon started")
        
        self.scheduler.run_reboot_jobs()
        
        try:
            self._run_loop()
        finally:
            self._cleanup()
            
    def _run_loop(self):
        while self.running:
            self.scheduler.tick()
            time.sleep(self.config.tick_interval_s)

    def _load_jobs(self):
        parser = WcrontabParser(self.config)
        try:
            jobs = parser.parse_all()
            self.scheduler.jobs = jobs
            logger.info(f"Loaded {len(jobs)} jobs")
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}")

    def _is_wcrond_process(self, pid: int) -> bool:
        """Check if the given PID belongs to a running wcrond process.
        
        Returns True only if the process exists AND its command line
        contains 'wcrond'. This prevents false positives after reboot
        when a different process reuses the PID.
        """
        if not psutil.pid_exists(pid):
            return False
        try:
            proc = psutil.Process(pid)
            cmdline = " ".join(proc.cmdline()).lower()
            return "wcrond" in cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False

    def stop(self):
        logger.info("Stopping wcrond daemon...")
        self.running = False
        
    def reload(self):
        logger.info("Reloading wcrond configuration...")
        self.config = WcrondConfig.load(self.config_path)
        self._load_jobs()
        
    def _handle_ipc_stop(self, req):
        self.stop()
        return {"status": "ok", "data": "stopping"}
        
    def _handle_ipc_reload(self, req):
        self.reload()
        return {"status": "ok", "data": "reloaded"}
        
    def _handle_ipc_list(self, req):
        jobs = []
        for j in self.scheduler.jobs.values():
            last_run = "Never"
            hist = self.state_store.get_history(j.job_id, limit=1)
            if hist:
                last_run = hist[0].start_time_utc

            jobs.append({
                "id": j.job_id,
                "schedule": j.schedule,
                "enabled": j.enabled,
                "last_run": last_run
            })
        return {"status": "ok", "data": jobs}
        
    def _handle_ipc_history(self, req):
        hist = self.state_store.get_history(req.get("job"), req.get("limit", 10), since=req.get("since"))
        data = []
        for h in hist:
            data.append({
                "job": h.job_id,
                "start_time": h.start_time_utc,
                "end_time": h.end_time_utc,
                "duration_s": h.duration_s,
                "status": h.status,
                "attempt": h.attempt,
                "trigger": h.trigger
            })
        return {"status": "ok", "data": data}
        
    def _handle_ipc_run(self, req):
        job_id = req.get("job")
        if not job_id:
            return {"status": "error", "message": "job ID required"}
        if job_id not in self.scheduler.jobs:
            return {"status": "error", "message": f"job {job_id} not found"}
        self.scheduler.force_run(job_id)
        return {"status": "ok", "data": "submitted"}
        
    def _handle_ipc_status(self, req):
        uptime = time.time() - self.start_time if self.start_time else 0
        jobs_count = len(self.scheduler.jobs)
        active_processes = len(self.executor.active_processes)
        retry_queue_size = len(self.state_store.get_retry_queue())
        return {
            "status": "ok",
            "data": {
                "uptime": uptime,
                "jobs": jobs_count,
                "threads": active_processes,
                "retry_queue_size": retry_queue_size
            }
        }

    def _handle_ipc_retries(self, req):
        data = self.state_store.get_retry_queue()
        # Ensure we match CLI expected fields: job, attempt, next_retry_at, reason
        formatted = []
        for r in data:
            formatted.append({
                "job": r.get("job_id", ""),
                "attempt": r.get("attempt", ""),
                "next_retry_at": r.get("next_retry_at", ""),
                "reason": r.get("reason", "")
            })
        return {"status": "ok", "data": formatted}

    def _handle_ipc_kill(self, req):
        job_id = req.get("job")
        if not job_id:
            return {"status": "error", "message": "job ID required"}
        # Find active executions for this job
        killed = 0
        for exec_id, process in list(self.executor.active_processes.items()):
            # We don't have job_id natively in active_processes, need to query state_store
            # Or we can just get running jobs
            running = self.state_store.get_running_jobs()
            for r in running:
                if r.job_id == job_id and r.execution_id == exec_id:
                    self.executor.kill(exec_id)
                    killed += 1
        return {"status": "ok", "data": f"killed {killed} processes"}

    def _handle_ipc_cancel_retry(self, req):
        job_id = req.get("job")
        if not job_id:
            return {"status": "error", "message": "job ID required"}
        self.retry_manager.cancel_retry(job_id)
        return {"status": "ok", "data": "cancelled"}

    def _handle_ipc_cancel_all_retries(self, req):
        try:
            cancelled = self.retry_manager.cancel_all()
            return {"status": "ok", "data": cancelled}
        except Exception as e:
            logger.error(f"Error cancelling all retries: {e}")
            return {"status": "error", "message": str(e)}

    def _handle_ipc_disable(self, req):
        job_id = req.get("job")
        if not job_id or job_id not in self.scheduler.jobs:
            return {"status": "error", "message": "job not found"}
        self.scheduler.jobs[job_id].enabled = False
        self.retry_manager.cancel_retry(job_id)
        return {"status": "ok", "data": "disabled"}

    def _handle_ipc_enable(self, req):
        job_id = req.get("job")
        if not job_id or job_id not in self.scheduler.jobs:
            return {"status": "error", "message": "job not found"}
        self.scheduler.jobs[job_id].enabled = True
        return {"status": "ok", "data": "enabled"}

    def _handle_ipc_zombies(self, req):
        zombies = self.watchdog.detect_zombies()
        return {"status": "ok", "data": zombies}

    def _handle_ipc_logs(self, req):
        job_id = req.get("job")
        tail = req.get("tail", 10)
        hist = self.state_store.get_history(job_id, limit=tail)
        logs = []
        for h in reversed(hist):
            if h.stdout_tail:
                logs.extend(h.stdout_tail.splitlines())
            if h.stderr_tail:
                logs.extend(h.stderr_tail.splitlines())
        return {"status": "ok", "data": logs[-tail:] if logs else []}

    def _handle_ipc_validate(self, req):
        # Already validated during load, check config limits
        warnings = []
        if self.config.tick_interval_s > 60:
            warnings.append(f"WARNING: tick_interval ({self.config.tick_interval_s}s) is greater than 60 seconds. Tasks scheduled during system suspension or hibernation will be lost.")
        return {"status": "ok", "data": {"status": "valid", "warnings": warnings}}

    def _handle_ipc_next(self, req):
        job_id = req.get("job")
        data = []
        if job_id:
            if job_id in self.scheduler.jobs:
                runs = self.scheduler.get_next_runs(job_id)
                for r in runs:
                    data.append({"job": job_id, "next_run": r.isoformat()})
        else:
            for jid in self.scheduler.jobs:
                runs = self.scheduler.get_next_runs(jid, n=1)
                if runs:
                    data.append({"job": jid, "next_run": runs[0].isoformat()})
        return {"status": "ok", "data": data}
        
    def _signal_handler(self, sig, frame):
        self.stop()
        
    def _cleanup(self):
        if self.ipc:
            self.ipc.stop()
        if self.watchdog:
            self.watchdog.stop()
        if self.retry_manager:
            self.retry_manager.cancel_all()
        if self.executor:
            self.executor.shutdown(wait=False)
        if self.state_store:
            self.state_store.close()
            
        try:
            pid_file = self.config.get_absolute_path(self.config.pid_file)
            if pid_file.exists():
                pid_file.unlink()
        except Exception as e:
            logger.error(f"Error removing PID file: {e}")
