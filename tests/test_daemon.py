import pytest
import os
import signal
from unittest.mock import patch, MagicMock
from pathlib import Path

from wcrond.daemon import WcrondDaemon
from wcrond.config import WcrondConfig
from wcrond.__main__ import main, send_ipc_command

@pytest.fixture
def mock_config(tmp_path):
    config = WcrondConfig(base_dir=tmp_path)
    config.pid_file = "test.pid"
    config.db_path = "test.db"
    config.ipc_pipe_name = f"\\\\.\\pipe\\wcrond_test_{os.getpid()}"
    return config

@patch("wcrond.daemon.WcrondConfig.load")
@patch("wcrond.daemon.IPCServer")
@patch("wcrond.daemon.Watchdog")
def test_daemon_lifecycle(mock_watchdog_cls, mock_ipc_cls, mock_load, mock_config):
    mock_load.return_value = mock_config
    mock_ipc = mock_ipc_cls.return_value
    mock_watchdog = mock_watchdog_cls.return_value
    
    daemon = WcrondDaemon()
    
    # Mock _run_loop to just set running to false so it exits
    def mock_run_loop():
        daemon.running = False
        
    with patch.object(daemon, '_run_loop', side_effect=mock_run_loop):
        daemon.start()
        
    assert daemon.config == mock_config
    assert daemon.state_store is not None
    assert daemon.executor is not None
    assert daemon.scheduler is not None
    assert daemon.retry_manager is not None
    
    mock_watchdog.start.assert_called_once()
    mock_ipc.start.assert_called_once()
    
    mock_watchdog.stop.assert_called_once()
    mock_ipc.stop.assert_called_once()
    
    # PID file should be removed on cleanup
    pid_file = mock_config.get_absolute_path(mock_config.pid_file)
    assert not pid_file.exists()

@patch("wcrond.daemon.WcrondConfig.load")
def test_daemon_stop_and_reload(mock_load, mock_config):
    mock_load.return_value = mock_config
    
    daemon = WcrondDaemon()
    daemon.config = mock_config
    # Mock scheduler
    daemon.scheduler = MagicMock()
    
    # test stop
    daemon.running = True
    daemon.stop()
    assert daemon.running is False
    
    # test reload
    daemon.reload()
    mock_load.assert_called()
    assert daemon.config == mock_config
    
    # test signal handler
    daemon.running = True
    daemon._signal_handler(signal.SIGINT, None)
    assert daemon.running is False

@patch("wcrond.daemon.WcrondConfig.load")
def test_daemon_ipc_handlers(mock_load, mock_config):
    mock_load.return_value = mock_config
    
    daemon = WcrondDaemon()
    daemon.config = mock_config
    daemon.scheduler = MagicMock()
    
    res = daemon._handle_ipc_stop({})
    assert res == {"status": "ok", "data": "stopping"}
    
    res = daemon._handle_ipc_reload({})
    assert res == {"status": "ok", "data": "reloaded"}

@patch("wcrond.daemon.WcrondConfig.load")
def test_daemon_new_ipc_handlers(mock_load, mock_config):
    mock_load.return_value = mock_config
    
    daemon = WcrondDaemon()
    daemon.config = mock_config
    daemon.start_time = 1000000.0
    daemon.scheduler = MagicMock()
    daemon.scheduler.jobs = {"job1": MagicMock(job_id="job1", enabled=True, schedule="* * * * *")}
    daemon.executor = MagicMock()
    daemon.executor.active_processes = {"exec1": MagicMock()}
    daemon.state_store = MagicMock()
    daemon.state_store.get_retry_queue.return_value = [{"job_id": "job1", "attempt": 2}]
    daemon.state_store.get_running_jobs.return_value = [MagicMock(job_id="job1", execution_id="exec1")]
    
    mock_history = MagicMock(start_time="2024-01-01T00:00:00", stdout_tail="hello", stderr_tail="")
    daemon.state_store.get_history.return_value = [mock_history]
    
    daemon.retry_manager = MagicMock()
    daemon.watchdog = MagicMock()
    daemon.watchdog.detect_zombies.return_value = []
    
    # 1. status
    res = daemon._handle_ipc_status({})
    assert res["status"] == "ok"
    assert res["data"]["jobs"] == 1
    assert res["data"]["threads"] == 1
    assert res["data"]["retry_queue_size"] == 1
    
    # 2. retries
    res = daemon._handle_ipc_retries({})
    assert res["status"] == "ok"
    assert len(res["data"]) == 1
    assert res["data"][0]["job"] == "job1"
    assert res["data"][0]["attempt"] == 2
    
    # 3. kill
    res = daemon._handle_ipc_kill({"job": "job1"})
    assert res["status"] == "ok"
    assert "killed 1 processes" in res["data"]
    daemon.executor.kill.assert_called_with("exec1")
    
    # 4. cancel-retry
    res = daemon._handle_ipc_cancel_retry({"job": "job1"})
    assert res["status"] == "ok"
    daemon.retry_manager.cancel_retry.assert_called_with("job1")
    
    # 5. disable / enable
    daemon.retry_manager.reset_mock()
    res = daemon._handle_ipc_disable({"job": "job1"})
    assert res["status"] == "ok"
    assert daemon.scheduler.jobs["job1"].enabled is False
    daemon.retry_manager.cancel_retry.assert_called_once_with("job1")
    
    res = daemon._handle_ipc_enable({"job": "job1"})
    assert res["status"] == "ok"
    assert daemon.scheduler.jobs["job1"].enabled is True
    
    # 6. zombies
    res = daemon._handle_ipc_zombies({})
    assert res["status"] == "ok"
    assert res["data"] == []
    
    # 7. logs
    res = daemon._handle_ipc_logs({"job": "job1", "tail": 10})
    assert res["status"] == "ok"
    assert "hello" in res["data"]
    
    # 8. validate
    res = daemon._handle_ipc_validate({})
    assert res["status"] == "ok"
    assert res["data"] == "valid"
    
    # 9. next
    daemon.scheduler.get_next_runs.return_value = [MagicMock(isoformat=lambda: "2024-01-01T00:00:00")]
    res = daemon._handle_ipc_next({"job": "job1"})
    assert res["status"] == "ok"
    assert len(res["data"]) == 1
    assert res["data"][0]["next_run"] == "2024-01-01T00:00:00"
    
    # 10. list (previous fix exact test)
    res = daemon._handle_ipc_list({})
    assert res["status"] == "ok"
    assert len(res["data"]) == 1
    assert res["data"][0]["id"] == "job1"
    assert res["data"][0]["last_run"] == "2024-01-01T00:00:00"

@patch("wcrond.__main__.WcrondDaemon")
@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "start", "--foreground"])
def test_main_start_foreground(mock_load, mock_daemon_cls, mock_config):
    mock_load.return_value = mock_config
    mock_daemon = mock_daemon_cls.return_value
    
    main()
    
    mock_daemon.start.assert_called_once()

@patch("wcrond.__main__.subprocess.Popen")
@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "start"])
def test_main_start_background(mock_load, mock_popen, mock_config):
    mock_load.return_value = mock_config
    
    main()
    
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    assert "start" in args[0]
    assert "--foreground" in args[0]

@patch("wcrond.__main__.send_ipc_command")
@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "stop"])
def test_main_stop(mock_load, mock_send_ipc, mock_config):
    mock_load.return_value = mock_config
    mock_send_ipc.return_value = {"status": "ok"}
    
    main()
    
    mock_send_ipc.assert_called_once()

@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "init"])
def test_main_init(mock_load, mock_config):
    mock_load.return_value = mock_config
    
    main()
    
    base = mock_config.base_dir
    assert (base / "wcrond.toml").exists()
    assert (base / "wcrontab.toml").exists()
    assert (base / "jobs.d").exists()

@patch("wcrond.__main__.win32file")
def test_send_ipc_command_success(mock_win32file, mock_config):
    # Mocking successful IPC communication
    mock_handle = MagicMock()
    mock_win32file.CreateFile.return_value = mock_handle
    mock_win32file.ReadFile.return_value = (0, b'{"status": "ok"}')
    
    res = send_ipc_command(mock_config, "test_cmd")
    
    assert res == {"status": "ok"}
    mock_win32file.WriteFile.assert_called_once()

@patch("wcrond.__main__.win32file")
def test_send_ipc_command_failure(mock_win32file, mock_config):
    # Mocking failed IPC communication
    mock_win32file.CreateFile.side_effect = Exception("Connection failed")
    
    res = send_ipc_command(mock_config, "test_cmd")
    
    assert res is None

@patch("wcrond.__main__.send_ipc_command")
@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "status"])
def test_main_status_running(mock_load, mock_send_ipc, mock_config):
    mock_load.return_value = mock_config
    mock_send_ipc.return_value = {"status": "ok", "data": {"uptime": 42.5}}
    
    with pytest.raises(SystemExit) as exc:
        main()
    
    assert exc.value.code == 0
    mock_send_ipc.assert_called_once()

@patch("wcrond.__main__.send_ipc_command")
@patch("wcrond.__main__.WcrondConfig.load")
@patch("sys.argv", ["wcrond", "status"])
def test_main_status_not_running(mock_load, mock_send_ipc, mock_config):
    mock_load.return_value = mock_config
    mock_send_ipc.return_value = None
    
    with pytest.raises(SystemExit) as exc:
        main()
    
    assert exc.value.code == 1
    mock_send_ipc.assert_called_once()
