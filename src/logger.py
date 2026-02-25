"""Centralized logging configuration for ReadIn AI desktop application.

This module provides a consistent logging setup across the application with:
- Console handler (INFO level) for standard output
- File handler (DEBUG level) with rotation at 5MB, keeping 3 backups
- Log location: ~/.readin/logs/readin.log
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log file configuration
LOG_DIR = Path.home() / ".readin" / "logs"
LOG_FILE = LOG_DIR / "readin.log"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3


def setup_logging() -> logging.Logger:
    """Setup and return the root application logger.

    Creates log directory if needed and configures both console and file handlers.

    Returns:
        The configured root logger for the application.
    """
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Get the root logger for the application
    logger = logging.getLogger("readin")

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler - INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # File handler - DEBUG level with rotation
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # If we can't create the file handler, log to console only
        logger.warning(f"Could not create log file handler: {e}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: The module name (typically __name__)

    Returns:
        A logger instance that inherits from the root 'readin' logger.
    """
    # Ensure root logger is configured
    setup_logging()

    # Create child logger
    if name.startswith("src."):
        # Strip 'src.' prefix for cleaner log names
        name = name[4:]

    return logging.getLogger(f"readin.{name}")


# Initialize logging on module import
_root_logger = setup_logging()
