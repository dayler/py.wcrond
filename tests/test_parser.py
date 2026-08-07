import pytest
from wcrond.config import WcrondConfig
from wcrond.parser import WcrontabParser

def test_parse_cronjob(wcrond_dir):
    config = WcrondConfig.load()
    (wcrond_dir / "wcrontab.toml").write_text('''
[jobs.test_job]
schedule = "*/5 * * * *"
command = "echo hello"
    ''')
    parser = WcrontabParser(config)
    jobs = parser.parse_all()
    assert "test_job" in jobs
    assert jobs["test_job"].command == "echo hello"
    assert jobs["test_job"].schedule == "*/5 * * * *"

def test_duplicate_job_ids(wcrond_dir):
    config = WcrondConfig.load()
    (wcrond_dir / "wcrontab.toml").write_text('''
[jobs.test_job]
schedule = "*/5 * * * *"
command = "echo hello"
    ''')
    jobs_d = wcrond_dir / "jobs.d"
    jobs_d.mkdir()
    (jobs_d / "extra.toml").write_text('''
[jobs.test_job]
schedule = "0 0 * * *"
command = "echo duplicate"
    ''')
    parser = WcrontabParser(config)
    with pytest.raises(ValueError, match="Duplicate job_id found"):
        parser.parse_all()

def test_invalid_cron_expression(wcrond_dir):
    config = WcrondConfig.load()
    (wcrond_dir / "wcrontab.toml").write_text('''
[jobs.test_job]
schedule = "invalid cron"
command = "echo hello"
    ''')
    parser = WcrontabParser(config)
    with pytest.raises(ValueError, match="Invalid cron expression"):
        parser.parse_all()

def test_cron_shortcuts(wcrond_dir):
    config = WcrondConfig.load()
    (wcrond_dir / "wcrontab.toml").write_text('''
[jobs.test_job]
schedule = "@daily"
command = "echo hello"
    ''')
    parser = WcrontabParser(config)
    jobs = parser.parse_all()
    assert jobs["test_job"].schedule == "0 0 * * *"

def test_overlap_policy_values(wcrond_dir):
    config = WcrondConfig.load()
    (wcrond_dir / "wcrontab.toml").write_text('''
[jobs.test_job]
schedule = "@daily"
command = "echo hello"
overlap_policy = "invalid_policy"
    ''')
    parser = WcrontabParser(config)
    with pytest.raises(ValueError, match="Invalid overlap_policy"):
        parser.parse_all()
