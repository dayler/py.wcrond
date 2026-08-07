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
