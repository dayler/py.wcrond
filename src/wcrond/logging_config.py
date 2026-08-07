import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from wcrond.config import WcrondConfig

def setup_logging(config: WcrondConfig):
    log_dir = config.get_absolute_path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "wcrond.log"
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.log_max_bytes,
        backupCount=config.log_backup_count,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if config.capture_job_output:
        jobs_log_dir = log_dir / "jobs"
        jobs_log_dir.mkdir(parents=True, exist_ok=True)
