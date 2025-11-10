"""Structured logging infrastructure for datawrapper-mcp.

This module provides:
- Console-based structured logging (text or JSON format)
- Correlation ID tracking across async operations
- Environment variable configuration
- Security: API tokens are never logged
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

# Context variable for correlation ID tracking across async operations
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add correlation ID if present
        cid = correlation_id.get()
        if cid:
            log_data['correlation_id'] = cid

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName',
                'relativeCreated', 'thread', 'threadName', 'exc_info',
                'exc_text', 'stack_info', 'taskName'
            ]:
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Configure logging based on environment variables.
    
    Environment Variables:
        DATAWRAPPER_MCP_LOG_LEVEL: Logging level (default: INFO)
            Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
        DATAWRAPPER_MCP_LOG_FORMAT: Log output format (default: text)
            Options: text, json
    
    Examples:
        # Text format with INFO level (default)
        DATAWRAPPER_MCP_LOG_LEVEL=INFO DATAWRAPPER_MCP_LOG_FORMAT=text
        
        # JSON format with DEBUG level
        DATAWRAPPER_MCP_LOG_LEVEL=DEBUG DATAWRAPPER_MCP_LOG_FORMAT=json
    """
    # Get configuration from environment
    log_level = os.getenv('DATAWRAPPER_MCP_LOG_LEVEL', 'INFO').upper()
    log_format = os.getenv('DATAWRAPPER_MCP_LOG_FORMAT', 'text').lower()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO
        print(
            f"Warning: Invalid log level '{log_level}', using INFO",
            file=sys.stderr
        )

    # Configure root logger
    root_logger = logging.getLogger('datawrapper_mcp')
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    # Set formatter based on format preference
    if log_format == 'json':
        formatter = JsonFormatter(
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        # Text format with correlation ID support
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Log startup message
    root_logger.info(
        'Logging initialized',
        extra={
            'log_level': log_level,
            'log_format': log_format,
        }
    )


def get_correlation_id() -> str:
    """Get or create correlation ID for current context.
    
    Returns:
        Correlation ID (UUID) for tracking operations across async calls.
        Creates a new UUID if one doesn't exist in the current context.
    """
    cid = correlation_id.get()
    if not cid:
        cid = str(uuid.uuid4())
        correlation_id.set(cid)
    return cid


def get_logger(name: str) -> logging.Logger:
    """Get a logger with correlation ID support.
    
    Args:
        name: Logger name (will be prefixed with 'datawrapper_mcp.')
    
    Returns:
        Configured logger instance
    
    Example:
        logger = get_logger('handlers.create')
        logger.info('Creating chart', extra={'chart_type': 'bar'})
    """
    return logging.getLogger(f'datawrapper_mcp.{name}')


def log_duration(start_time: float) -> int:
    """Calculate duration in milliseconds from start time.
    
    Args:
        start_time: Start time from time.time()
    
    Returns:
        Duration in milliseconds
    """
    return int((time.time() - start_time) * 1000)
