import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, call
from wcrond.scheduler import Scheduler
from wcrond.job import CronJob
from wcrond.state import StateStore, TaskExecution

@pytest.fixture
def state_store():
    store = Mock(spec=StateStore)
    store.get_running_jobs.return_value = []
    return store

@pytest.fixture
def executor():
    return Mock()

@pytest.fixture
def scheduler(state_store, executor):
    s = Scheduler(state_store)
    s.set_executor(executor)
    return s

def test_tick_detects_minute_boundary(scheduler, executor):
    dt1 = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.tick(dt1)
    
    job = CronJob(job_id="test", schedule="* * * * *", command="echo")
    scheduler.add_job(job)
    
    # Tick again in the same minute shouldn't submit
    dt2 = datetime(2026, 8, 7, 10, 30, 30, tzinfo=timezone.utc)
    scheduler.tick(dt2)
    executor.submit_job.assert_not_called()
    
    # Tick in next minute should submit
    dt3 = datetime(2026, 8, 7, 10, 31, 0, tzinfo=timezone.utc)
    scheduler.tick(dt3)
    executor.submit_job.assert_called_once()

def test_tick_no_action_same_minute(scheduler, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo")
    scheduler.add_job(job)
    dt1 = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.tick(dt1)
    
    assert executor.submit_job.call_count == 1
    
    dt2 = datetime(2026, 8, 7, 10, 30, 59, tzinfo=timezone.utc)
    scheduler.tick(dt2)
    assert executor.submit_job.call_count == 1  # Still 1

def test_evaluate_matching_job(scheduler, executor):
    job = CronJob(job_id="test", schedule="30 10 * * *", command="echo")
    scheduler.add_job(job)
    # Use a specific local timezone to ensure croniter evaluates based on the datetime's hour/minute
    tz_local = timezone(timedelta(hours=-4))
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=tz_local)
    scheduler.evaluate_jobs(dt)
    executor.submit_job.assert_called_once_with(job, trigger="scheduled")

def test_evaluate_local_timezone(scheduler, executor):
    job = CronJob(job_id="test", schedule="0 18 * * *", command="echo")
    scheduler.add_job(job)
    # If the user sets local time to 18:00 (e.g. UTC-4), it should match 18:00
    tz_local = timezone(timedelta(hours=-4))
    dt_local = datetime(2026, 8, 7, 18, 0, 0, tzinfo=tz_local)
    scheduler.evaluate_jobs(dt_local)
    executor.submit_job.assert_called_once_with(job, trigger="scheduled")
    
    # If the time is 18:00 UTC (which is 14:00 local), it should NOT match for local eval
    executor.submit_job.reset_mock()
    dt_utc = datetime(2026, 8, 7, 18, 0, 0, tzinfo=timezone.utc)
    # The tick generates a local time of 14:00 when it's 18:00 UTC
    dt_local_2 = dt_utc.astimezone(tz_local) # 14:00 local
    scheduler.evaluate_jobs(dt_local_2)
    executor.submit_job.assert_not_called()

def test_evaluate_non_matching_job(scheduler, executor):
    job = CronJob(job_id="test", schedule="31 10 * * *", command="echo")
    scheduler.add_job(job)
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    executor.submit_job.assert_not_called()

def test_evaluate_disabled_job(scheduler, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo", enabled=False)
    scheduler.add_job(job)
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    executor.submit_job.assert_not_called()

def test_overlap_skip(scheduler, state_store, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo", overlap_policy="skip")
    scheduler.add_job(job)
    
    state_store.get_running_jobs.return_value = [
        TaskExecution(execution_id="123", job_id="test", job_name="test", start_time_utc="", start_time_local=None, end_time_utc=None, end_time_local=None, duration_s=None, exit_code=None, status="RUNNING", attempt=1, pid=123, stdout_tail="", stderr_tail="", trigger="scheduled")
    ]
    
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    executor.submit_job.assert_not_called()

def test_overlap_allow(scheduler, state_store, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo", overlap_policy="allow")
    scheduler.add_job(job)
    
    state_store.get_running_jobs.return_value = [
        TaskExecution(execution_id="123", job_id="test", job_name="test", start_time_utc="", start_time_local=None, end_time_utc=None, end_time_local=None, duration_s=None, exit_code=None, status="RUNNING", attempt=1, pid=123, stdout_tail="", stderr_tail="", trigger="scheduled")
    ]
    
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    executor.submit_job.assert_called_once()

def test_overlap_kill_previous(scheduler, state_store, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo", overlap_policy="kill_previous")
    scheduler.add_job(job)
    
    state_store.get_running_jobs.return_value = [
        TaskExecution(execution_id="123", job_id="test", job_name="test", start_time_utc="", start_time_local=None, end_time_utc=None, end_time_local=None, duration_s=None, exit_code=None, status="RUNNING", attempt=1, pid=123, stdout_tail="", stderr_tail="", trigger="scheduled")
    ]
    
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    executor.kill.assert_called_once_with("123")
    executor.submit_job.assert_called_once()

def test_reboot_jobs_at_startup(scheduler, executor):
    job = CronJob(job_id="test", schedule="@reboot", command="echo")
    scheduler.add_job(job)
    scheduler.run_reboot_jobs()
    executor.submit_job.assert_called_once_with(job, trigger="reboot")

def test_force_run(scheduler, executor):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo")
    scheduler.add_job(job)
    scheduler.force_run("test")
    executor.submit_job.assert_called_once_with(job, trigger="manual")

def test_disable_enable_job(scheduler):
    job = CronJob(job_id="test", schedule="* * * * *", command="echo")
    scheduler.add_job(job)
    
    scheduler.disable_job("test")
    assert not scheduler.jobs["test"].enabled
    
    scheduler.enable_job("test")
    assert scheduler.jobs["test"].enabled

def test_get_next_runs(scheduler):
    job = CronJob(job_id="test", schedule="0 0 * * *", command="echo")  # Daily
    scheduler.add_job(job)
    runs = scheduler.get_next_runs("test", 3)
    assert len(runs) == 3

def test_multiple_jobs_same_minute(scheduler, executor):
    job1 = CronJob(job_id="test1", schedule="* * * * *", command="echo")
    job2 = CronJob(job_id="test2", schedule="* * * * *", command="echo")
    scheduler.add_job(job1)
    scheduler.add_job(job2)
    
    dt = datetime(2026, 8, 7, 10, 30, 0, tzinfo=timezone.utc)
    scheduler.evaluate_jobs(dt)
    assert executor.submit_job.call_count == 2
