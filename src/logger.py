"""Logger module for rpi-tft-camera.

Provides centralized logging with configurable levels and output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class Logger:
    """Simple logger with console and file output."""
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        log_to_file: bool = True,
        log_to_console: bool = True,
        log_file: Optional[Path] = None
    ):
        """Initialize logger.
        
        Args:
            name: Logger name (usually module name)
            level: Log level (logging.DEBUG, INFO, WARNING, ERROR)
            log_to_file: Enable file logging
            log_to_console: Enable console logging
            log_file: Custom log file path (default: logs/app.log)
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        
        # Remove existing handlers
        self._logger.handlers.clear()
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            self._logger.addHandler(console_handler)
        
        # File handler
        if log_to_file:
            log_path = log_file or Path.home() / ".cache" / "opencode" / "rpi-tft-camera" / "app.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path)
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            self._logger.addHandler(file_handler)
    
    def debug(self, msg: str) -> None:
        """Log debug message."""
        self._logger.debug(msg)
    
    def info(self, msg: str) -> None:
        """Log info message."""
        self._logger.info(msg)
    
    def warning(self, msg: str) -> None:
        """Log warning message."""
        self._logger.warning(msg)
    
    def error(self, msg: str) -> None:
        """Log error message."""
        self._logger.error(msg)
    
    def exception(self, msg: str, exc_info: bool = True) -> None:
        """Log exception message."""
        self._logger.exception(msg) if exc_info else self._logger.error(msg)


# Create module-level loggers
def get_logger(name: str) -> Logger:
    """Get or create a logger for a module.
    
    Args:
        name: Module name (usually __name__)
    
    Returns:
        Logger instance
    """
    return Logger(name=name)
