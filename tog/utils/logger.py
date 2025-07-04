import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# Create package-level loggers
console_logger = logging.getLogger('tog')
file_logger = logging.getLogger('tog.file')

def initialize_loggers(
    log_dir="logs",
    log_filename="tog.log",
    console_level=logging.ERROR,  # Changed default to ERROR
    file_level=logging.ERROR,    # Changed default to ERROR
    when="midnight",
    backup_count=7,
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
):
    """Initialize both console and file loggers for the tog package."""
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    formatter = logging.Formatter(fmt)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    console_logger.addHandler(console_handler)
    console_logger.setLevel(console_level)

    # File Handler with rotation
    file_handler = TimedRotatingFileHandler(
        log_path / log_filename,
        when=when,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level)
    file_logger.addHandler(file_handler)
    file_logger.setLevel(file_level)

def set_log_level(level):
    """Set log level for all tog loggers."""
    console_logger.setLevel(level)
    file_logger.setLevel(level)

# Initialize loggers with ERROR level
initialize_loggers()

# Keep these for backward compatibility
def setup_logger(*args, **kwargs):
    """Deprecated: Use console_logger or file_logger instead."""
    import warnings
    warnings.warn("setup_logger is deprecated. Use tog.utils.logger.console_logger instead", DeprecationWarning)
    return console_logger

def setup_default_logging():
    """Deprecated: Use initialize_loggers instead."""
    import warnings
    warnings.warn("setup_default_logging is deprecated. Use tog.utils.logger.initialize_loggers instead", DeprecationWarning)
    initialize_loggers()
