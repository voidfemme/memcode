"""
Logging configuration for MemCode.
Provides structured logging with proper formatting.
"""

import logging
import sys
import os
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup structured logging for the application."""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper())
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str):
    """Get a logger instance."""
    return logging.getLogger(name)


# Setup logging on module import
log_level = os.getenv("LOG_LEVEL", "INFO")
setup_logging(log_level)
