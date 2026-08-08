import pytest
import os
import time
from unittest.mock import MagicMock, patch
from wcrond.executor import Executor
from wcrond.job import CronJob
from wcrond.config import WcrondConfig

@pytest.fixture
def config():
    return WcrondConfig()

@pytest.fixture
def state_store():
    store = MagicMock()
    store.record_start.return_value = "exec_1"
    return store

@pytest.fixture
def executor(config, state_store):
    ex = Executor(config, state_store)
    yield ex
    ex.shutdown()

def test_execute_success(executor, state_store):
    job = CronJob(job_id="test", command="echo success", schedule="* * * * *")
    executor.execute_job(job, "scheduled", 1)
    
    state_store.record_start.assert_called_once()
    state_store.record_end.assert_called_once()
    call_args = state_store.record_end.call_args[1]
    assert call_args["exit_code"] == 0
    assert call_args["status"] == "SUCCESS"
    assert "success" in call_args["stdout_tail"].lower()

def test_execute_failure(executor, state_store):
    job = CronJob(job_id="test", command="exit 1", shell="cmd", schedule="* * * * *")
    executor.execute_job(job, "scheduled", 1)
    
    call_args = state_store.record_end.call_args[1]
    assert call_args["exit_code"] != 0
    assert call_args["status"] == "FAILED"

def test_execute_timeout(executor, state_store):
    job = CronJob(job_id="test", command="Start-Sleep -Seconds 5", shell="powershell", schedule="* * * * *", timeout=1)
    executor.execute_job(job, "scheduled", 1)
    
    call_args = state_store.record_end.call_args[1]
    assert call_args["status"] == "TIMEOUT"

def test_execute_env_vars(executor, state_store):
    job = CronJob(job_id="test", command="echo %MY_TEST_VAR%", shell="cmd", schedule="* * * * *", env={"MY_TEST_VAR": "HELLO_WCROND"})
    executor.execute_job(job, "scheduled", 1)
    
    call_args = state_store.record_end.call_args[1]
    assert "HELLO_WCROND" in call_args["stdout_tail"]

def test_execute_working_dir(executor, state_store, tmp_path):
    job = CronJob(job_id="test", command="cd", shell="cmd", schedule="* * * * *", working_dir=str(tmp_path))
    executor.execute_job(job, "scheduled", 1)
    
    call_args = state_store.record_end.call_args[1]
    assert str(tmp_path).lower() in call_args["stdout_tail"].lower()

def test_shell_cmd(executor, state_store):
    job = CronJob(job_id="test", command="echo from cmd", shell="cmd", schedule="* * * * *")
    executor.execute_job(job, "scheduled", 1)
    assert "from cmd" in state_store.record_end.call_args[1]["stdout_tail"].lower()

def test_shell_powershell(executor, state_store):
    job = CronJob(job_id="test", command="Write-Output 'from pwsh'", shell="powershell", schedule="* * * * *")
    executor.execute_job(job, "scheduled", 1)
    assert "from pwsh" in state_store.record_end.call_args[1]["stdout_tail"].lower()

def test_stdout_stderr_capture(executor, state_store):
    job = CronJob(job_id="test", command="echo out && echo err 1>&2", shell="cmd", schedule="* * * * *")
    executor.execute_job(job, "scheduled", 1)
    
    call_args = state_store.record_end.call_args[1]
    assert "out" in call_args["stdout_tail"].lower()
    assert "err" in call_args["stderr_tail"].lower()

def test_thread_pool_bounded(executor, state_store):
    import concurrent.futures
    executor.config.pool_size = 2
    executor.pool.shutdown()
    executor.pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    job = CronJob(job_id="test", command="Start-Sleep -Seconds 2", shell="powershell", schedule="* * * * *")
    
    t0 = time.time()
    for _ in range(4):
        executor.submit_job(job)
    executor.pool.shutdown(wait=True)
    duration = time.time() - t0
    
    assert duration >= 3.0  # Since pool size is 2, 4 jobs of 2s take at least 4s total.

@patch('subprocess.Popen')
def test_create_new_process_group(mock_popen, executor, state_store):
    mock_popen.return_value.communicate.return_value = ("out", "err")
    mock_popen.return_value.returncode = 0
    job = CronJob(job_id="test", command="echo test", schedule="* * * * *", silent=False)
    executor.execute_job(job, "scheduled", 1)
    
    # In Windows subprocess.CREATE_NEW_PROCESS_GROUP is 512
    # Ensure creationflags is passed and matches CREATE_NEW_PROCESS_GROUP
    call_args = mock_popen.call_args[1]
    import subprocess
    creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
    assert call_args["creationflags"] == creationflags

@patch('subprocess.Popen')
def test_create_no_window_silent(mock_popen, executor, state_store):
    mock_popen.return_value.communicate.return_value = ("out", "err")
    mock_popen.return_value.returncode = 0
    job = CronJob(job_id="test", command="echo test", schedule="* * * * *", silent=True)
    executor.execute_job(job, "scheduled", 1)
    
    call_args = mock_popen.call_args[1]
    import subprocess
    creationflags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 512)
    creationflags |= 0x08000000
    assert call_args["creationflags"] == creationflags
