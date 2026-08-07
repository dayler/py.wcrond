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
        
    def start(self):
        # 1. Load config
        self.config = WcrondConfig.load(self.config_path)
        
        # 2. PID file
        pid_file = self.config.get_absolute_path(self.config.pid_file)
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text().strip())
                if psutil.pid_exists(old_pid):
                    logger.error(f"wcrond is already running with PID {old_pid}")
                    sys.exit(1)
            except Exception:
                pass
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
        
        # 6. IPC
        self.ipc = IPCServer(self.config.ipc_pipe_name)
        # Register daemon specific handlers
        self.ipc.handlers["stop"] = self._handle_ipc_stop
        self.ipc.handlers["reload"] = self._handle_ipc_reload
        self.ipc.handlers["list"] = self._handle_ipc_list
        self.ipc.handlers["history"] = self._handle_ipc_history
        self.ipc.handlers["run"] = self._handle_ipc_run
        self.ipc.start()
        
        # 7. Setup signals
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGBREAK, self._signal_handler)
        except AttributeError:
            pass
        
        self.running = True
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
            jobs.append({
                "id": j.job_id,
                "schedule": j.schedule,
                "enabled": True, # TODO enabled
                "last_run": "Never"
            })
        return {"status": "ok", "data": jobs}
        
    def _handle_ipc_history(self, req):
        hist = self.state_store.get_history(req.get("job"), req.get("limit", 10))
        data = []
        for h in hist:
            data.append({
                "job": h.job_id,
                "start_time": h.start_time,
                "end_time": h.end_time,
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
