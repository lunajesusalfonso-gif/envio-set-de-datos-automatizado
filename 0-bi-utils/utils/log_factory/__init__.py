"""API pública de la utilidad de logging."""

from .log_factory import get_logger, purge_log_file

__all__ = ["get_logger", "purge_log_file"]
