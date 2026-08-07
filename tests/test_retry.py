import pytest
import time
from unittest.mock import MagicMock
from wcrond.retry import RetryManager
from wcrond.job import CronJob, RetryConfig

@pytest.fixture
def state_store():
    store = MagicMock()
    return store

@pytest.fixture
def callback():
    return MagicMock()

@pytest.fixture
def retry_manager(state_store, callback):
    rm = RetryManager(state_store, callback)
    yield rm
    rm.cancel_all()

def test_retry_delay_calculation(retry_manager):
    # test backoff delay internally
    job = CronJob(job_id="test", command="echo", schedule="* * * * *", 
                  retry=RetryConfig(initial_delay_s=1, backoff_multiplier=2.0, max_delay_s=10))
    
    with pytest.MonkeyPatch.context() as m:
        timer_mock = MagicMock()
        m.setattr("threading.Timer", timer_mock)
        
        retry_manager.schedule_retry(job, attempt=2)
        assert timer_mock.call_args[0][0] == 1
        
        retry_manager.schedule_retry(job, attempt=3)
        assert timer_mock.call_args[0][0] == 2
        
        retry_manager.schedule_retry(job, attempt=4)
        assert timer_mock.call_args[0][0] == 4

def test_retry_max_delay(retry_manager):
    job = CronJob(job_id="test", command="echo", schedule="* * * * *", 
                  retry=RetryConfig(max_retries=10, initial_delay_s=1, backoff_multiplier=2.0, max_delay_s=2))
                  
    with pytest.MonkeyPatch.context() as m:
        timer_mock = MagicMock()
        m.setattr("threading.Timer", timer_mock)
        retry_manager.schedule_retry(job, attempt=10) # 9th retry execution
        assert timer_mock.call_args[0][0] == 2

def test_retry_schedule_and_execute(retry_manager, callback):
    job = CronJob(job_id="test", command="echo", schedule="* * * * *", 
                  retry=RetryConfig(initial_delay_s=0, backoff_multiplier=1.0, max_delay_s=1))
    
    retry_manager.schedule_retry(job, attempt=2)
    time.sleep(0.1) # wait for timer
    callback.assert_called_once_with(job, "retry", 2)

def test_retry_cancel(retry_manager, callback):
    job = CronJob(job_id="test", command="echo", schedule="* * * * *", 
                  retry=RetryConfig(initial_delay_s=1, backoff_multiplier=1.0, max_delay_s=1))
    
    retry_manager.schedule_retry(job, attempt=2)
    retry_manager.cancel_retry("test")
    time.sleep(1.2)
    callback.assert_not_called()

def test_retry_cancel_all(retry_manager, callback):
    job1 = CronJob(job_id="test1", command="echo", schedule="* * * * *", retry=RetryConfig(initial_delay_s=1))
    job2 = CronJob(job_id="test2", command="echo", schedule="* * * * *", retry=RetryConfig(initial_delay_s=1))
    
    retry_manager.schedule_retry(job1, attempt=2)
    retry_manager.schedule_retry(job2, attempt=2)
    
    retry_manager.cancel_all()
    time.sleep(1.2)
    callback.assert_not_called()

def test_retry_max_retries(retry_manager, callback):
    job = CronJob(job_id="test", command="echo", schedule="* * * * *", 
                  retry=RetryConfig(max_retries=3, initial_delay_s=1))
                  
    retry_manager.schedule_retry(job, attempt=5) # This should not schedule (attempt > max_retries + 1)
    assert "test" not in retry_manager.timers
