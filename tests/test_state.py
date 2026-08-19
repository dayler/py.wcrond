import pytest
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from wcrond.state import StateStore, TaskExecution

@pytest.fixture
def store():
    # Use in-memory database for tests
    store = StateStore(":memory:")
    yield store
    store.close()

def test_create_tables(store):
    cursor = store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row["name"] for row in cursor.fetchall()}
    assert "executions" in tables
    assert "retry_queue" in tables

def test_record_start(store):
    exec_id = store.record_start("job1", "Job 1", 1234, "scheduled", 1)
    
    cursor = store.conn.execute("SELECT * FROM executions WHERE execution_id = ?", (exec_id,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row["job_id"] == "job1"
    assert row["job_name"] == "Job 1"
    assert row["status"] == "RUNNING"
    assert row["attempt"] == 1
    assert row["pid"] == 1234
    assert row["trigger"] == "scheduled"
    assert row["start_time_utc"] is not None
    assert row["start_time_local"] is not None
    assert row["end_time_utc"] is None
    assert row["end_time_local"] is None

def test_record_end(store):
    exec_id = store.record_start("job1", "Job 1", 1234, "scheduled", 1)
    store.record_end(exec_id, 0, "SUCCESS", "hello", "world")
    
    cursor = store.conn.execute("SELECT * FROM executions WHERE execution_id = ?", (exec_id,))
    row = cursor.fetchone()
    
    assert row["status"] == "SUCCESS"
    assert row["exit_code"] == 0
    assert row["stdout_tail"] == "hello"
    assert row["stderr_tail"] == "world"
    assert row["end_time_utc"] is not None
    assert row["end_time_local"] is not None
    assert row["duration_s"] is not None

def test_record_full_lifecycle(store):
    exec_id = store.record_start("job2", "Job 2", None, "manual", 1)
    store.record_end(exec_id, 1, "FAILED", None, "error")
    
    history = store.get_history()
    assert len(history) == 1
    
    exec_obj = history[0]
    assert exec_obj.execution_id == exec_id
    assert exec_obj.job_id == "job2"
    assert exec_obj.status == "FAILED"
    assert exec_obj.exit_code == 1
    assert exec_obj.duration_s >= 0

def test_get_history_all(store):
    store.record_start("job1", "Job 1", None, "manual", 1)
    store.record_start("job2", "Job 2", None, "manual", 1)
    
    history = store.get_history()
    assert len(history) == 2

def test_get_history_by_job(store):
    store.record_start("job1", "Job 1", None, "manual", 1)
    store.record_start("job2", "Job 2", None, "manual", 1)
    
    history = store.get_history(job_id="job1")
    assert len(history) == 1
    assert history[0].job_id == "job1"

def test_get_history_limit(store):
    for i in range(5):
        store.record_start(f"job{i}", f"Job {i}", None, "manual", 1)
    
    history = store.get_history(limit=3)
    assert len(history) == 3

def test_get_running_jobs(store):
    exec1 = store.record_start("job1", "Job 1", None, "manual", 1)
    store.record_start("job2", "Job 2", None, "manual", 1)
    
    store.record_end(exec1, 0, "SUCCESS", None, None)
    
    running = store.get_running_jobs()
    assert len(running) == 1
    assert running[0].job_id == "job2"

def test_add_retry(store):
    now = datetime.now(timezone.utc).isoformat()
    store.add_retry("job1", 2, now, "Timeout")
    
    queue = store.get_retry_queue()
    assert len(queue) == 1
    assert queue[0]["job_id"] == "job1"
    assert queue[0]["attempt"] == 2
    assert queue[0]["reason"] == "Timeout"

def test_remove_retry(store):
    now = datetime.now(timezone.utc).isoformat()
    store.add_retry("job1", 2, now, "Timeout")
    store.remove_retry("job1")
    
    queue = store.get_retry_queue()
    assert len(queue) == 0

def test_get_retry_queue(store):
    store.add_retry("job1", 2, "2026-08-08T10:00:00+00:00", "Reason 1")
    store.add_retry("job2", 3, "2026-08-08T09:00:00+00:00", "Reason 2")
    
    queue = store.get_retry_queue()
    assert len(queue) == 2
    # Should be sorted by next_retry_at ASC
    assert queue[0]["job_id"] == "job2"
    assert queue[1]["job_id"] == "job1"

def test_cleanup_old_records(store):
    # Insert old record manually
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("old_exec", "job1", "Job 1", old_time, "SUCCESS", 1, "manual")
    )
    # Insert recent record
    recent_time = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("recent_exec", "job1", "Job 1", recent_time, "SUCCESS", 1, "manual")
    )

    store.cleanup_old_records(days=5)

    history = store.get_history()
    assert len(history) == 1
    assert history[0].execution_id == "recent_exec"

def test_thread_safety(store):
    def worker(job_id):
        exec_id = store.record_start(job_id, f"Job {job_id}", None, "scheduled", 1)
        store.record_end(exec_id, 0, "SUCCESS", None, None)

    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(f"job{i}",))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    history = store.get_history(limit=100)
    assert len(history) == 10

def test_status_values(store):
    # Just verifying status values are stored as provided
    exec_id = store.record_start("job1", "Job 1", None, "manual", 1)
    store.record_end(exec_id, 0, "TIMEOUT", None, None)

    history = store.get_history()
    assert history[0].status == "TIMEOUT"

def test_get_history_with_since_filter(store):
    # Insert an old record (10 days ago)
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("old_exec", "job1", "Job 1", old_time, "SUCCESS", 1, "manual")
    )
    # Insert a recent record (1 day ago)
    recent_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("recent_exec", "job1", "Job 1", recent_time, "SUCCESS", 1, "manual")
    )

    # Filter since 5 days ago
    since = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    history = store.get_history(since=since)
    assert len(history) == 1
    assert history[0].execution_id == "recent_exec"


def test_get_history_with_job_and_since(store):
    old_time = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    recent_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("exec1", "job1", "Job 1", old_time, "SUCCESS", 1, "manual")
    )
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("exec2", "job1", "Job 1", recent_time, "SUCCESS", 1, "manual")
    )
    store.conn.execute(
        "INSERT INTO executions (execution_id, job_id, job_name, start_time_utc, status, attempt, trigger) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("exec3", "job2", "Job 2", recent_time, "SUCCESS", 1, "manual")
    )

    since = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    history = store.get_history(job_id="job1", since=since)
    assert len(history) == 1
    assert history[0].execution_id == "exec2"


# --- New tests for UTC/local time columns ---

def test_start_time_local_is_populated(store):
    """record_start must populate start_time_local with a non-null value."""
    exec_id = store.record_start("job1", "Job 1", None, "scheduled", 1)
    history = store.get_history()
    assert len(history) == 1
    assert history[0].start_time_local is not None
    assert history[0].start_time_local != ""


def test_end_time_local_is_populated(store):
    """record_end must populate end_time_local with a non-null value."""
    exec_id = store.record_start("job1", "Job 1", None, "scheduled", 1)
    store.record_end(exec_id, 0, "SUCCESS", None, None)
    history = store.get_history()
    assert history[0].end_time_local is not None
    assert history[0].end_time_local != ""


def test_local_times_are_valid_iso(store):
    """start_time_local and end_time_local must be parseable ISO strings."""
    exec_id = store.record_start("job1", "Job 1", None, "scheduled", 1)
    store.record_end(exec_id, 0, "SUCCESS", None, None)
    history = store.get_history()
    rec = history[0]
    # Should not raise
    start_local_dt = datetime.fromisoformat(rec.start_time_local)
    end_local_dt = datetime.fromisoformat(rec.end_time_local)
    assert start_local_dt <= end_local_dt


def test_local_time_has_timezone_offset(store):
    """Local time strings must carry a UTC offset (not naive datetimes)."""
    exec_id = store.record_start("job1", "Job 1", None, "scheduled", 1)
    store.record_end(exec_id, 0, "SUCCESS", None, None)
    history = store.get_history()
    rec = history[0]
    start_local_dt = datetime.fromisoformat(rec.start_time_local)
    end_local_dt = datetime.fromisoformat(rec.end_time_local)
    assert start_local_dt.tzinfo is not None, "start_time_local must be timezone-aware"
    assert end_local_dt.tzinfo is not None, "end_time_local must be timezone-aware"


def test_dataclass_fields_new_columns(store):
    """TaskExecution dataclass must expose start_time_utc, start_time_local,
    end_time_utc, and end_time_local fields after record_start/record_end."""
    exec_id = store.record_start("job1", "Job 1", None, "scheduled", 1)
    store.record_end(exec_id, 0, "SUCCESS", "out", "err")
    history = store.get_history()
    rec = history[0]
    # Old fields must NOT exist
    assert not hasattr(rec, "start_time"), "Old field 'start_time' must be removed"
    assert not hasattr(rec, "end_time"), "Old field 'end_time' must be removed"
    # New fields must exist
    assert hasattr(rec, "start_time_utc")
    assert hasattr(rec, "start_time_local")
    assert hasattr(rec, "end_time_utc")
    assert hasattr(rec, "end_time_local")
