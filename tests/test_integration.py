import pytest
import os
import time
import threading
from pathlib import Path
from wcrond.daemon import WcrondDaemon
from wcrond.config import WcrondConfig
from wcrond.state import StateStore
from wcrond.job import CronJob
from unittest.mock import patch

@pytest.fixture
def test_config(tmp_path):
    config = WcrondConfig(base_dir=tmp_path)
    config.db_path = "wcrond.db"
    config.pid_file = "wcrond.pid"
    config.tick_interval_s = 0.1
    config.watchdog_interval_s = 0.2
    config.ipc_pipe_name = f"\\\\.\\pipe\\wcrond_test_{os.getpid()}_{time.time()}"
    return config

@pytest.fixture
def daemon_runner(test_config):
    daemon = WcrondDaemon()
    daemon.config_path = str(test_config.base_dir / "wcrond.toml")
    pipe_name = test_config.ipc_pipe_name.replace('\\', '\\\\')
    Path(daemon.config_path).write_text(f"""
db_path = "wcrond.db"
pid_file = "wcrond.pid"
tick_interval_s = 0.1
watchdog_interval_s = 0.2
ipc_pipe_name = "{pipe_name}"
""")
    
    
    # We'll run start() in a thread
    thread = threading.Thread(target=daemon.start)
    thread.daemon = True
    
    with patch("signal.signal"):
        yield daemon, thread, test_config
    
    daemon.stop()
    if thread.is_alive():
        thread.join(timeout=2.0)

def wait_for_job(store: StateStore, job_id: str, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        hist = store.get_history(job_id, 1)
        if hist:
            job = hist[0]
            if job.status in ("SUCCESS", "FAILED", "TIMEOUT", "SKIPPED"):
                return job
        time.sleep(0.1)
    return None

def test_full_job_lifecycle(daemon_runner):
    daemon, thread, config = daemon_runner
    
    # Write a job config
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / "test.toml"
    job_file.write_text("""
[jobs.test_job]
command = "echo hello integration"
schedule = "* * * * *"
""")

    thread.start()
    time.sleep(0.5)  # Wait for daemon to load jobs
    
    # Trigger job manually
    daemon.scheduler.force_run("test_job")
    
    # Check DB
    job = wait_for_job(daemon.state_store, "test_job")
    assert job is not None
    assert job.status == "SUCCESS"

def test_retry_full_flow(daemon_runner):
    daemon, thread, config = daemon_runner
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    # A job that fails
    job_file = jobs_dir / "retry.toml"
    job_file.write_text("""
[jobs.fail_job]
command = "exit 1"
schedule = "* * * * *"
shell = "cmd"

[jobs.fail_job.retry]
max_retries = 2
initial_delay_s = 0
backoff_multiplier = 1.0
""")

    thread.start()
    time.sleep(0.5)
    
    daemon.scheduler.force_run("fail_job")
    
    # wait for retries exhausted
    for _ in range(120):
        hist = daemon.state_store.get_history("fail_job", 10)
        if len(hist) >= 3:
            break
        time.sleep(0.1)
    
    assert len(hist) == 3

def test_retry_max_exhausted(daemon_runner):
    # Already covered by test_retry_full_flow
    pass

def test_watchdog_kills_zombie(daemon_runner):
    daemon, thread, config = daemon_runner
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / "zombie.toml"
    job_file.write_text("""
[jobs.zombie_job]
command = "Start-Sleep -Seconds 10"
shell = "powershell"
schedule = "* * * * *"
timeout = 1
""")

    thread.start()
    time.sleep(0.5)
    
    daemon.scheduler.force_run("zombie_job")
    
    job = wait_for_job(daemon.state_store, "zombie_job", timeout=5.0)
    assert job is not None
    assert job.status == "TIMEOUT"

def test_overlap_skip_integration(daemon_runner):
    daemon, thread, config = daemon_runner
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / "skip.toml"
    job_file.write_text("""
[jobs.skip_job]
command = "Start-Sleep -Seconds 3"
shell = "powershell"
schedule = "* * * * *"
overlap_policy = "skip"
""")

    thread.start()
    time.sleep(0.5)
    
    daemon.scheduler.force_run("skip_job")
    time.sleep(0.5)
    daemon.scheduler.force_run("skip_job")
    
    time.sleep(0.5)
    hist = daemon.state_store.get_history("skip_job", 10)
    assert len(hist) == 1

def test_overlap_kill_previous(daemon_runner):
    daemon, thread, config = daemon_runner
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_file = jobs_dir / "kill.toml"
    job_file.write_text("""
[jobs.kill_job]
command = "Start-Sleep -Seconds 5"
shell = "powershell"
schedule = "* * * * *"
overlap_policy = "kill_previous"
""")

    thread.start()
    time.sleep(0.5)
    
    daemon.scheduler.force_run("kill_job")
    time.sleep(1.0)
    daemon.scheduler.force_run("kill_job")
    
    time.sleep(1.0)
    hist = daemon.state_store.get_history("kill_job", 10)
    killed = [h for h in hist if h.status == "FAILED"]
    assert len(killed) > 0

def test_hot_reload(daemon_runner):
    daemon, thread, config = daemon_runner
    jobs_dir = config.get_absolute_path("jobs.d")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    
    thread.start()
    time.sleep(0.5)
    assert "reload_job" not in daemon.scheduler.jobs
    
    job_file = jobs_dir / "reload.toml"
    job_file.write_text("""
[jobs.reload_job]
command = "echo hi"
schedule = "* * * * *"
""")
    
    daemon.reload()
    assert "reload_job" in daemon.scheduler.jobs

def test_graceful_shutdown(daemon_runner):
    daemon, thread, config = daemon_runner
    thread.start()
    time.sleep(0.5)
    
    daemon.stop()
    thread.join(timeout=2.0)
    assert not thread.is_alive()
