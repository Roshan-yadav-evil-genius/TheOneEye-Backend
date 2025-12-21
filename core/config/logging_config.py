"""
Logging configuration for the workflow orchestrator using structlog.

Configures structlog with:
- Pretty console output (human-readable, colored)
- JSON file output (machine-readable, structured)
- Daily log file rotation (UTC)
- Log files named with UTC date: workflow_YYYY-MM-DD.log
"""

import logging
import structlog
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import sys


def setup_logging():
    """
    Configure structlog with pretty console and JSON file output.

    This should be called once at application startup (e.g., in main()).
    After calling this, modules can use: logger = structlog.get_logger(__name__)
    """
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Shared processors for both console and file
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
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()

    # Console handler with pretty output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True),
        foreign_pre_chain=shared_processors,
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with JSON output and daily rotation (UTC)
    file_handler = TimedRotatingFileHandler(
        filename=logs_dir / "workflow.jsonl",
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding="utf-8",
        utc=True,  # Use UTC for rotation
    )
    file_handler.suffix = "%Y-%m-%d.jsonl"  # Creates workflow_2024-01-15.log
    file_handler.setLevel(logging.DEBUG)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
