import pytest
from unittest.mock import patch, MagicMock
from wcrond_ctl import cli, formatters
import argparse

def test_formatter_duration():
    assert formatters.format_duration(30) == "30.0s"
    assert formatters.format_duration(65) == "1m 5s"
    assert formatters.format_duration(3605) == "1h 0m"
    assert formatters.format_duration(None) == "-"

def test_formatter_colors():
    assert "\033[92m" in formatters.colorize("SUCCESS", "SUCCESS")
    assert "\033[91m" in formatters.colorize("FAILED", "FAILED")
    assert "\033[94m" in formatters.colorize("RUNNING", "RUNNING")
    assert "\033[93m" in formatters.colorize("TIMEOUT", "TIMEOUT")
    assert formatters.colorize("UNKNOWN", "UNKNOWN") == "UNKNOWN"

def test_formatter_table(capsys):
    formatters.print_table(["A", "B"], [["1", "2"], ["3", "4"]])
    out, _ = capsys.readouterr()
    assert "A" in out
    assert "B" in out
    assert "1" in out
    assert "2" in out
    assert "3" in out
    assert "4" in out
    assert "│" in out

def test_cli_help(capsys):
    with patch("sys.argv", ["wcrond-ctl", "--help"]):
        with pytest.raises(SystemExit):
            cli.main()
    out, _ = capsys.readouterr()
    assert "help" in out

def test_cli_status_command():
    args = argparse.Namespace(command="status")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": {"uptime": 100, "jobs": 2}}
    cli.cmd_status(args, client)
    client.send_request.assert_called_with({"cmd": "status"})

def test_cli_list_command():
    args = argparse.Namespace(command="list")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": []}
    cli.cmd_list(args, client)
    client.send_request.assert_called_with({"cmd": "list"})

def test_cli_history_flags():
    args = argparse.Namespace(command="history", job="job1", last=5, since="2026-08-01")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": []}
    cli.cmd_history(args, client)
    client.send_request.assert_called_with({"cmd": "history", "job": "job1", "limit": 5, "since": "2026-08-01"})

def test_cli_run_command():
    args = argparse.Namespace(command="run", job_id="test_job")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "submitted"}
    cli.cmd_run(args, client)
    client.send_request.assert_called_with({"cmd": "run", "job": "test_job"})

def test_cli_retries_command():
    args = argparse.Namespace(command="retries")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": [{"job": "j1", "attempt": 1, "next_retry_at": "now", "reason": "fail"}]}
    cli.cmd_retries(args, client)
    client.send_request.assert_called_with({"cmd": "retries"})

def test_cli_kill_command():
    args = argparse.Namespace(command="kill", job_id="test_job")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "killed"}
    cli.cmd_kill(args, client)
    client.send_request.assert_called_with({"cmd": "kill", "job": "test_job"})

def test_cli_cancel_retry_command():
    args = argparse.Namespace(command="cancel-retry", job_id="test_job")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "cancelled"}
    cli.cmd_cancel_retry(args, client)
    client.send_request.assert_called_with({"cmd": "cancel-retry", "job": "test_job"})

def test_cli_disable_command():
    args = argparse.Namespace(command="disable", job_id="test_job")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "disabled"}
    cli.cmd_disable(args, client)
    client.send_request.assert_called_with({"cmd": "disable", "job": "test_job"})

def test_cli_enable_command():
    args = argparse.Namespace(command="enable", job_id="test_job")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "enabled"}
    cli.cmd_enable(args, client)
    client.send_request.assert_called_with({"cmd": "enable", "job": "test_job"})

def test_cli_zombies_command():
    args = argparse.Namespace(command="zombies")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": [{"job": "z1", "pid": 123, "since": "now"}]}
    cli.cmd_zombies(args, client)
    client.send_request.assert_called_with({"cmd": "zombies"})

def test_cli_reload_command():
    args = argparse.Namespace(command="reload")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "reloaded"}
    cli.cmd_reload(args, client)
    client.send_request.assert_called_with({"cmd": "reload"})

def test_cli_logs_command():
    args = argparse.Namespace(command="logs", job="j1", tail=10)
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": ["line1", "line2"]}
    cli.cmd_logs(args, client)
    client.send_request.assert_called_with({"cmd": "logs", "job": "j1", "tail": 10})

def test_cli_validate_command():
    args = argparse.Namespace(command="validate")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "valid"}
    cli.cmd_validate(args, client)
    client.send_request.assert_called_with({"cmd": "validate"})

def test_cli_next_command():
    args = argparse.Namespace(command="next", job="j1")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": [{"job": "j1", "next_run": "later"}]}
    cli.cmd_next(args, client)
    client.send_request.assert_called_with({"cmd": "next", "job": "j1"})

def test_cli_stop_command():
    args = argparse.Namespace(command="stop")
    client = MagicMock()
    client.send_request.return_value = {"status": "ok", "data": "stopping"}
    cli.cmd_stop(args, client)
    client.send_request.assert_called_with({"cmd": "stop"})

def test_cli_error_response():
    args = argparse.Namespace(command="status")
    client = MagicMock()
    client.send_request.return_value = {"status": "error", "message": "Test error"}
    with pytest.raises(SystemExit):
        cli.cmd_status(args, client)

def test_main_dispatch(monkeypatch):
    monkeypatch.setattr("sys.argv", ["wcrond-ctl", "status"])
    monkeypatch.setattr("wcrond_ctl.cli.cmd_status", MagicMock())
    cli.main()


def test_global_timeout_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["wcrond-ctl", "--timeout", "10", "status"])
    mock_cmd_status = MagicMock()
    monkeypatch.setattr("wcrond_ctl.cli.cmd_status", mock_cmd_status)
    cli.main()
    # Verify cmd_status was called with args that have timeout=10.0
    call_args = mock_cmd_status.call_args[0]
    assert call_args[0].timeout == 10.0


def test_default_timeout_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["wcrond-ctl", "status"])
    mock_cmd_status = MagicMock()
    monkeypatch.setattr("wcrond_ctl.cli.cmd_status", mock_cmd_status)
    cli.main()
    call_args = mock_cmd_status.call_args[0]
    assert call_args[0].timeout == 5.0

