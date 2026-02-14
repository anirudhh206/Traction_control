"""Structured Logging Configuration."""

import sys
import logging
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger

from config import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    processors: list[Any] = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if settings.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logging to any class."""
    
    @property
    def logger(self) -> FilteringBoundLogger:
        """Get logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger