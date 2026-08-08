import subprocess
import os
import time
import logging
from typing import Optional, Callable
from collections import deque
import concurrent.futures

from wcrond.job import CronJob
from wcrond.state import StateStore
from wcrond.config import WcrondConfig
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Executor:
    def __init__(self, config: WcrondConfig, state_store: StateStore, retry_manager=None):
        self.config = config
        self.state_store = state_store
        self.retry_manager = retry_manager
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.pool_size)
        self.active_processes = {}

    def shutdown(self, wait=True):
        for p in self.active_processes.values():
            try:
                p.terminate()
            except Exception:
                pass
        self.pool.shutdown(wait=wait)

    def kill(self, execution_id: str):
        p = self.active_processes.get(execution_id)
        if p:
            try:
                p.terminate()
            except Exception:
                pass

    def submit_job(self, job: CronJob, trigger: str = "scheduled", attempt: int = 1):
        # We assume the caller handles overlap policies if needed.
        self.pool.submit(self.execute_job, job, trigger, attempt)

    def execute_job(self, job: CronJob, trigger: str, attempt: int):
        # 1. Environment
        env = os.environ.copy()
        if job.env:
            env.update(job.env)
            
        # Expand working dir
        cwd = job.working_dir or self.config.default_working_dir
        if cwd:
            cwd = os.path.expandvars(cwd)
            if not os.path.exists(cwd):
                logger.warning(f"Working directory {cwd} does not exist for job {job.job_id}. Using current.")
                cwd = None
        else:
            cwd = None

        # 2. Shell mapping
        shell = job.shell or self.config.default_shell
        cmd_args = self._build_cmd_args(shell, job.command)
        
        # 3. Timeouts
        timeout = job.timeout if job.timeout is not None else self.config.default_timeout
        
        logger.info(f"Executing job {job.job_id} (attempt {attempt}, trigger {trigger})")
        
        process = None
        execution_id = None
        
        try:
            # subprocess.CREATE_NEW_PROCESS_GROUP = 512 in windows
            creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
            if job.silent:
                creationflags |= 0x08000000
            
            process = subprocess.Popen(
                cmd_args,
                env=env,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags
            )
            
            execution_id = self.state_store.record_start(
                job_id=job.job_id,
                job_name=job.name,
                pid=process.pid,
                trigger=trigger,
                attempt=attempt
            )
            self.active_processes[execution_id] = process
            
            stdout, stderr = process.communicate(timeout=timeout)
            
            exit_code = process.returncode
            status = "SUCCESS" if exit_code == 0 else "FAILED"
            
            stdout_tail = self._tail(stdout, self.config.output_tail_lines)
            stderr_tail = self._tail(stderr, self.config.output_tail_lines)
            
            self._write_job_logs(job, stdout, stderr)

            self.state_store.record_end(
                execution_id=execution_id,
                exit_code=exit_code,
                status=status,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail
            )
            
            # Execute hooks
            if exit_code == 0:
                self._run_hook(job, job.on_success)
            else:
                self._run_hook(job, job.on_failure)

            if exit_code != 0 and self.retry_manager:
                if attempt <= job.retry.max_retries:
                    self.retry_manager.schedule_retry(job, attempt + 1, f"exit code {exit_code}")
                    
        except subprocess.TimeoutExpired:
            if process:
                logger.warning(f"Job {job.job_id} timed out after {timeout}s")
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=self.config.grace_period)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                
                status = "TIMEOUT"
                stdout_tail = self._tail(stdout, self.config.output_tail_lines)
                stderr_tail = self._tail(stderr, self.config.output_tail_lines)
                
                self._write_job_logs(job, stdout, stderr)

                if execution_id:
                    self.state_store.record_end(
                        execution_id=execution_id,
                        exit_code=-1, # Or some timeout code
                        status=status,
                        stdout_tail=stdout_tail,
                        stderr_tail=stderr_tail
                    )
                    self._run_hook(job, job.on_failure)
                
                if self.retry_manager and attempt <= job.retry.max_retries:
                    self.retry_manager.schedule_retry(job, attempt + 1, "timeout")

        except Exception as e:
            logger.exception(f"Error executing job {job.job_id}: {e}")
            if execution_id:
                self.state_store.record_end(
                    execution_id=execution_id,
                    exit_code=-1,
                    status="FAILED",
                    stdout_tail="",
                    stderr_tail=str(e)
                )
        finally:
            if execution_id:
                self.active_processes.pop(execution_id, None)

    def _build_cmd_args(self, shell: str, command: str) -> list:
        shell = shell.lower()
        if shell == "cmd":
            return ["cmd.exe", "/c", command]
        elif shell == "powershell":
            return ["powershell.exe", "-NoProfile", "-Command", command]
        elif shell == "pwsh":
            return ["pwsh.exe", "-NoProfile", "-Command", command]
        elif shell == "bash":
            return ["bash", "-c", command]
        else:
            # Assume absolute path
            return [shell, command]

    def _tail(self, text: Optional[str], lines: int) -> str:
        if not text:
            return ""
        all_lines = text.splitlines()
        return "\n".join(all_lines[-lines:])

    def _write_job_logs(self, job: CronJob, stdout: str, stderr: str):
        """Write full stdout/stderr to individual log files per job execution."""
        if not self.config.capture_job_output:
            return
        try:
            log_dir = self.config.get_absolute_path(self.config.log_dir) / "jobs" / job.job_id
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
            if stdout:
                (log_dir / f"{timestamp}.stdout.log").write_text(stdout, encoding="utf-8")
            if stderr:
                (log_dir / f"{timestamp}.stderr.log").write_text(stderr, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to write job logs for {job.job_id}: {e}")

    def _run_hook(self, job: CronJob, hook_command: str):
        """Execute a hook command (on_success/on_failure) as a fire-and-forget subprocess."""
        if not hook_command:
            return
        try:
            shell = job.shell or self.config.default_shell
            cmd_args = self._build_cmd_args(shell, hook_command)
            creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
            creationflags |= 0x08000000  # CREATE_NO_WINDOW, hooks are always silent
            subprocess.Popen(
                cmd_args,
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Hook executed for job {job.job_id}: {hook_command}")
        except Exception as e:
            logger.error(f"Failed to run hook for job {job.job_id}: {e}")
