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
