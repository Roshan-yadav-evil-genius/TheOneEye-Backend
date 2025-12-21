"""
Unified logging configuration using structlog.

This module provides a single source of truth for logging configuration
that works across Django web app, Celery workers, management commands, and future services.

All logs go to one unified file (django.jsonl) with structured JSON output
and colored console output.
"""

# Import stdlib logging explicitly to avoid shadowing issues
import logging as stdlib_logging
import structlog
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

# Ensure we use stdlib logging, not our local module
logging = stdlib_logging


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


def setup_logging(base_dir=None):
    """
    Configure structlog and return Django LOGGING dict.
    
    This function is idempotent - safe to call multiple times.
    It configures structlog processors and returns a LOGGING dict
    that Django will use to set up handlers.
    
    Args:
        base_dir: Base directory for log files (defaults to current working directory)
        
    Returns:
        dict: Django LOGGING configuration dictionary
    """
    # Resolve log directory first (always needed for LOGGING dict)
    if base_dir is None:
        base_dir = Path.cwd()
    elif isinstance(base_dir, str):
        base_dir = Path(base_dir)
    
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Idempotency check: only configure structlog if not already configured
    # But always return the full LOGGING dict so Django can set up handlers
    if not structlog.is_configured():
        # Shared processors for both console and file formatters
        shared_processors = [
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
        ]
        
        # Configure structlog to use stdlib integration
        structlog.configure(
            processors=shared_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            cache_logger_on_first_use=True,
        )
    
    # Always define shared processors for formatters (even if structlog was already configured)
    shared_processors = [
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
    ]
    
    # Return Django LOGGING configuration dict
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'console': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.dev.ConsoleRenderer(colors=True),
                'foreign_pre_chain': shared_processors,
            },
            'json': {
                '()': structlog.stdlib.ProcessorFormatter,
                'processor': structlog.processors.JSONRenderer(),
                'foreign_pre_chain': shared_processors,
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'level': 'INFO',
            },
            'console_debug': {
                'class': 'logging.StreamHandler',
                'formatter': 'console',
                'level': 'DEBUG',
            },
            'file': {
                '()': 'app_logging.config.DjangoTimedRotatingFileHandler',
                'filename': str(logs_dir / 'django.jsonl'),
                'when': 'midnight',
                'interval': 1,
                'backupCount': 30,
                'encoding': 'utf-8',
                'utc': True,
                'suffix': '%Y-%m-%d.jsonl',
                'formatter': 'json',
                'level': 'DEBUG',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.server': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
            'apps.browsersession': {
                'handlers': ['console_debug', 'file'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'apps.workflow': {
                'handlers': ['console', 'file'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }

