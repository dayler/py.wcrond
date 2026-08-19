import pytest
from unittest.mock import MagicMock, patch
from wcrond.watchdog import Watchdog
from wcrond.config import WcrondConfig
from wcrond.state import TaskExecution
from datetime import datetime, timezone, timedelta
import time

@pytest.fixture
def config():
    c = WcrondConfig()
    c.default_timeout = 2
    return c

@pytest.fixture
def state_store():
    return MagicMock()

@pytest.fixture
def watchdog(config, state_store):
    return Watchdog(state_store, config)

def test_watchdog_detect_zombie(watchdog, state_store):
    now = datetime.now(timezone.utc)
    old_start = (now - timedelta(seconds=10)).isoformat()

    state_store.get_running_jobs.return_value = [
        TaskExecution(execution_id="exec_1", job_id="job_1", job_name="job_1",
                      start_time_utc=old_start, start_time_local=None,
                      end_time_utc=None, end_time_local=None,
                      duration_s=None, exit_code=None, status="RUNNING",
                      attempt=1, pid=999999, stdout_tail=None, stderr_tail=None,
                      trigger="scheduled")
    ]

    with patch("psutil.pid_exists", return_value=True):
        zombies = watchdog.detect_zombies()
        assert len(zombies) == 1
        assert zombies[0].execution_id == "exec_1"

def test_watchdog_no_false_positives(watchdog, state_store):
    now = datetime.now(timezone.utc)
    recent_start = (now - timedelta(seconds=1)).isoformat()

    state_store.get_running_jobs.return_value = [
        TaskExecution(execution_id="exec_1", job_id="job_1", job_name="job_1",
                      start_time_utc=recent_start, start_time_local=None,
                      end_time_utc=None, end_time_local=None,
                      duration_s=None, exit_code=None, status="RUNNING",
                      attempt=1, pid=999999, stdout_tail=None, stderr_tail=None,
                      trigger="scheduled")
    ]

    with patch("psutil.pid_exists", return_value=True):
        zombies = watchdog.detect_zombies()
        assert len(zombies) == 0

@patch("psutil.Process")
def test_watchdog_kill_zombie(mock_process, watchdog, state_store):
    mock_p = MagicMock()
    mock_process.return_value = mock_p

    zombie = TaskExecution(execution_id="exec_1", job_id="job_1", job_name="job_1",
                           start_time_utc="2026-08-01T00:00:00+00:00", start_time_local=None,
                           end_time_utc=None, end_time_local=None,
                           duration_s=None, exit_code=None, status="RUNNING",
                           attempt=1, pid=1234, stdout_tail=None, stderr_tail=None,
                           trigger="scheduled")

    watchdog.kill_zombie(zombie)

    mock_p.terminate.assert_called_once()
    mock_p.wait.assert_called_once()
    state_store.record_end.assert_called_once()

@patch("psutil.Process")
def test_watchdog_grace_period(mock_process, watchdog, state_store):
    import psutil
    mock_p = MagicMock()
    mock_process.return_value = mock_p
    mock_p.wait.side_effect = psutil.TimeoutExpired(1)

    zombie = TaskExecution(execution_id="exec_1", job_id="job_1", job_name="job_1",
                           start_time_utc="2026-08-01T00:00:00+00:00", start_time_local=None,
                           end_time_utc=None, end_time_local=None,
                           duration_s=None, exit_code=None, status="RUNNING",
                           attempt=1, pid=1234, stdout_tail=None, stderr_tail=None,
                           trigger="scheduled")

    watchdog.kill_zombie(zombie)

    mock_p.terminate.assert_called_once()
    mock_p.kill.assert_called_once()

def test_periodic_cleanup(config, state_store):
    config.cleanup_interval_hours = 0  # Force immediate cleanup on first call
    config.history_retention_days = 30
    wd = Watchdog(state_store, config)
    wd._maybe_cleanup()
    state_store.cleanup_old_records.assert_called_once_with(30)


def test_periodic_cleanup_skips_when_not_due(config, state_store):
    config.cleanup_interval_hours = 24
    config.history_retention_days = 30
    wd = Watchdog(state_store, config)
    wd._last_cleanup = time.time()  # Just cleaned up
    wd._maybe_cleanup()
    state_store.cleanup_old_records.assert_not_called()

