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

@patch('subprocess.Popen')
def test_on_success_hook_called(mock_popen, executor, state_store):
    # Main process mock
    main_process = MagicMock()
    main_process.communicate.return_value = ("out", "err")
    main_process.returncode = 0
    # Hook process mock
    hook_process = MagicMock()
    mock_popen.side_effect = [main_process, hook_process]
    
    job = CronJob(job_id="test", command="echo test", schedule="* * * * *",
                  on_success="echo success_hook", on_failure=None)
    executor.execute_job(job, "scheduled", 1)
    
    # Popen should be called twice: once for the job, once for the hook
    assert mock_popen.call_count == 2
    hook_call_args = mock_popen.call_args_list[1]
    assert "success_hook" in str(hook_call_args)


@patch('subprocess.Popen')
def test_on_failure_hook_called(mock_popen, executor, state_store):
    main_process = MagicMock()
    main_process.communicate.return_value = ("out", "err")
    main_process.returncode = 1
    hook_process = MagicMock()
    mock_popen.side_effect = [main_process, hook_process]
    
    job = CronJob(job_id="test", command="echo test", schedule="* * * * *",
                  on_success=None, on_failure="echo failure_hook")
    executor.execute_job(job, "scheduled", 1)
    
    assert mock_popen.call_count == 2
    hook_call_args = mock_popen.call_args_list[1]
    assert "failure_hook" in str(hook_call_args)


@patch('subprocess.Popen')
def test_no_hook_when_not_configured(mock_popen, executor, state_store):
    main_process = MagicMock()
    main_process.communicate.return_value = ("out", "err")
    main_process.returncode = 0
    mock_popen.return_value = main_process
    
    job = CronJob(job_id="test", command="echo test", schedule="* * * * *",
                  on_success=None, on_failure=None)
    executor.execute_job(job, "scheduled", 1)
    
    # Popen called only once (for the job, no hook)
    assert mock_popen.call_count == 1

def test_capture_job_output_writes_files(state_store, tmp_path):
    config = WcrondConfig(base_dir=tmp_path)
    config.capture_job_output = True
    config.log_dir = "logs"
    ex = Executor(config, state_store)
    
    job = CronJob(job_id="log_test", command="echo captured_output", shell="cmd", schedule="* * * * *")
    ex.execute_job(job, "scheduled", 1)
    ex.shutdown()
    
    log_dir = tmp_path / "logs" / "jobs" / "log_test"
    assert log_dir.exists()
    stdout_files = list(log_dir.glob("*.stdout.log"))
    assert len(stdout_files) == 1
    content = stdout_files[0].read_text(encoding="utf-8")
    assert "captured_output" in content


def test_no_capture_when_disabled(state_store, tmp_path):
    config = WcrondConfig(base_dir=tmp_path)
    config.capture_job_output = False
    config.log_dir = "logs"
    ex = Executor(config, state_store)
    
    job = CronJob(job_id="no_log", command="echo test", shell="cmd", schedule="* * * * *")
    ex.execute_job(job, "scheduled", 1)
    ex.shutdown()
    
    log_dir = tmp_path / "logs" / "jobs" / "no_log"
    assert not log_dir.exists()
