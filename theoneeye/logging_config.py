"""
Logging configuration for Django using structlog.

Configures structlog with:
- Pretty console output (human-readable, colored) for development
- JSON file output (machine-readable, structured) for production
- Daily log file rotation (UTC)
- Django-specific context (request_id, user_id, etc.)
- Separate log files: django.jsonl (vs core's workflow.jsonl)
"""

import logging
import structlog
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import sys


class DjangoTimedRotatingFileHandler(TimedRotatingFileHandler):
    """
    Custom TimedRotatingFileHandler that accepts suffix in constructor.
    
    This allows Django's LOGGING configuration to set the suffix directly.
    """
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, 
                 delay=False, utc=False, atTime=None, suffix=None):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc, atTime)
        if suffix is not None:
            self.suffix = suffix


def setup_django_logging():
    """
    Configure structlog for Django.
    
    This ensures structlog is properly configured before Django starts.
    Handlers are configured via Django's LOGGING setting in settings.py.
    This should be called once at Django application startup (e.g., in wsgi.py/asgi.py).
    After calling this, modules can use: logger = structlog.get_logger(__name__)
    """
    # Create logs directory (relative to backend directory) to ensure it exists
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Configure structlog to use stdlib integration
    # Note: This may be called multiple times (once in settings.py, once here)
    # but structlog.configure() is idempotent and the last call wins
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO
                ]
            ),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )

