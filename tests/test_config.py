import pytest
from wcrond.config import WcrondConfig
from wcrond.logging_config import setup_logging
import logging
import logging.handlers

def test_load_default_config(temp_home):
    config = WcrondConfig.load()
    assert config.pool_size == 4
    assert config.tick_interval_s == 1.0

def test_load_custom_config(wcrond_dir):
    config_file = wcrond_dir / "wcrond.toml"
    config_file.write_text('''
[daemon]
tick_interval = 2.5
[pool]
max_workers = 8
    ''')
    config = WcrondConfig.load()
    assert config.tick_interval_s == 2.5
    assert config.pool_size == 8

def test_config_path_resolution(temp_home):
    config = WcrondConfig.load()
    abs_path = config.get_absolute_path("logs/wcrond.log")
    assert abs_path.is_absolute()

def test_logging_config_setup(temp_home, wcrond_dir):
    config = WcrondConfig.load()
    setup_logging(config)
    
    logger = logging.getLogger()
    assert logger.level == logging.INFO
    assert any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers)
