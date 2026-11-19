"""Lectura estricta de valores desde archivos YAML."""

from pathlib import Path
from typing import Any

import yaml


def read_yaml_value(
    file_path: str | Path,
    key_path: str,
    default: Any | None = None,
    must_exist: bool = True,
) -> Any:
    """Lee un valor de un YAML mediante una ruta de claves separadas por puntos."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"No existe un archivo YAML válido en: {path}")

    try:
        with path.open("r", encoding="utf-8") as file_stream:
            content = yaml.safe_load(file_stream)
    except yaml.YAMLError as error:
        raise ValueError(f"El archivo YAML contiene sintaxis inválida: {path}") from error

    if content is None:
        raise ValueError(f"El archivo YAML está vacío: {path}")

    current: Any = content
    traversed_keys: list[str] = []
    for key in key_path.split("."):
        traversed_keys.append(key)
        if not isinstance(current, dict) or key not in current:
            if must_exist:
                missing_path = ".".join(traversed_keys)
                raise KeyError(
                    f"No existe el elemento: '{missing_path}' en el archivo .yaml"
                )
            return default
        current = current[key]

    return current
