"""Configuración de loggers y purga de archivos de registro."""

from __future__ import annotations

import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


_LOG_TIMESTAMP = re.compile(
    r"^\w+\s*\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    module_id: str,
    log_dir: str | Path | None = None,
    debug_mode: bool = False,
) -> logging.Logger:
    """Obtiene un logger configurado para consola o archivo."""
    logger = logging.getLogger(module_id)

    for previous_handler in logger.handlers[:]:
        logger.removeHandler(previous_handler)
        previous_handler.close()

    logger.propagate = False
    formatter = logging.Formatter(
        "%(levelname)s | %(asctime)s | %(name)s | %(message)s",
        datefmt=_TIMESTAMP_FORMAT,
    )

    if debug_mode:
        logger.setLevel(logging.DEBUG)
        handler: logging.Handler = logging.StreamHandler(sys.stdout)
    else:
        if log_dir is None:
            raise ValueError("log_dir es obligatorio cuando debug_mode=False")

        destination = Path(log_dir)
        destination.mkdir(parents=True, exist_ok=True)
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(
            destination / f"{module_id}.log",
            encoding="utf-8",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def purge_log_file(file_path: str | Path, retention_days: int) -> int:
    """Elimina líneas anteriores al periodo indicado y devuelve su cantidad."""
    if (
        isinstance(retention_days, bool)
        or not isinstance(retention_days, int)
        or retention_days < 0
    ):
        raise ValueError("retention_days debe ser un número entero no negativo")

    path = Path(file_path)
    if not path.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=retention_days)
    retained_lines: list[str] = []
    removed_count = 0

    with path.open("r", encoding="utf-8", newline="") as source:
        for line in source:
            match = _LOG_TIMESTAMP.match(line)
            if match is None:
                retained_lines.append(line)
                continue

            try:
                timestamp = datetime.strptime(match.group(1), _TIMESTAMP_FORMAT)
            except ValueError:
                retained_lines.append(line)
                continue

            if timestamp < cutoff:
                removed_count += 1
            else:
                retained_lines.append(line)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.writelines(retained_lines)
            temporary_path = Path(temporary_file.name)

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return removed_count


__all__ = ["get_logger", "purge_log_file"]
