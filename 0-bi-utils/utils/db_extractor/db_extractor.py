"""Extracción de consultas SQL hacia ``pandas.DataFrame``."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter
from warnings import warn

import pandas as pd
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError


class DatabaseAuthenticationError(SQLAlchemyError):
    """Indica que el motor rechazó la autenticación del usuario."""


def _read_sql_file(sql_path: str | Path) -> str:
    """Lee un archivo SQL existente usando codificación UTF-8."""
    path = Path(sql_path)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo SQL: {path}")
    return path.read_text(encoding="utf-8")


def _validate_timeouts(
    connection_timeout: int,
    execution_timeout: int,
    socket_timeout: int,
) -> None:
    """Comprueba que todos los timeouts sean enteros positivos."""
    timeouts = {
        "connection_timeout": connection_timeout,
        "execution_timeout": execution_timeout,
        "socket_timeout": socket_timeout,
    }
    for name, value in timeouts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"El timeout {name} debe ser un número entero positivo"
            )


def _validate_required_connection_fields(
    field_types: dict[str, type],
    **fields: object,
) -> None:
    """Distingue parámetros de conexión faltantes de valores inválidos."""
    for name, value in fields.items():
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError(
                f"Falta el parámetro obligatorio de conexión: {name}"
            )

        expected_type = field_types[name]
        if expected_type is str and isinstance(value, str):
            continue
        if expected_type is int:
            if isinstance(value, int) and not isinstance(value, bool) and value > 0:
                continue

        raise ValueError(f"Parámetro de conexión inválido: {name}")


def _is_authentication_error(error: SQLAlchemyError) -> bool:
    """Reconoce las señales de autenticación emitidas por HANA y SQL Server."""
    messages = [str(error)]
    original_error = getattr(error, "orig", None)
    if original_error is not None:
        messages.append(str(original_error))
        messages.extend(str(argument) for argument in getattr(original_error, "args", ()))

    normalized_message = " ".join(messages).casefold()
    indicators = (
        "28000",
        "18456",
        "authentication failed",
        "login failed",
        "invalid user name or password",
        "invalid username or password",
        "invalid user or password",
    )
    return any(indicator in normalized_message for indicator in indicators)


def _execute_query(
    query: str,
    url: URL,
    connect_args: dict[str, int],
    database_engine: str,
    execution_timeout: int,
    socket_timeout: int,
) -> pd.DataFrame:
    """Ejecuta la consulta, clasifica autenticación y libera el engine."""
    engine = None
    started_at = perf_counter()
    try:
        engine = create_engine(url, connect_args=connect_args)
        if database_engine == "SAP HANA":
            event.listen(
                engine,
                "before_cursor_execute",
                lambda _conn, cursor, _statement, _parameters, _context, _many: (
                    cursor.setquerytimeout(execution_timeout)
                ),
            )
        else:
            event.listen(
                engine,
                "connect",
                lambda dbapi_connection, _connection_record: setattr(
                    dbapi_connection,
                    "timeout",
                    execution_timeout,
                ),
            )
        with engine.connect() as connection:
            result = pd.read_sql_query(text(query), connection)
        elapsed = perf_counter() - started_at
        if elapsed > socket_timeout:
            warn(
                "La consulta toma más tiempo del máximo definido "
                f"por socket_timeout ({socket_timeout} segundos)",
                RuntimeWarning,
                stacklevel=2,
            )
        return result
    except SQLAlchemyError as error:
        if _is_authentication_error(error):
            raise DatabaseAuthenticationError(
                f"Error de autenticación en {database_engine}: "
                "verifica el usuario y la contraseña"
            ) from error
        raise
    finally:
        if engine is not None:
            engine.dispose()


def query_hana(
    sql_path: str | Path,
    user: str,
    password: str,
    host: str,
    port: int,
    database: str | None = None,
    connection_timeout: int = 5,
    execution_timeout: int = 300,
    socket_timeout: int = 300,
) -> pd.DataFrame:
    """Ejecuta un archivo SQL en SAP HANA y devuelve su resultado."""
    _validate_required_connection_fields(
        {"user": str, "password": str, "host": str, "port": int},
        user=user,
        password=password,
        host=host,
        port=port,
    )
    _validate_timeouts(
        connection_timeout,
        execution_timeout,
        socket_timeout,
    )
    query = _read_sql_file(sql_path)
    url = URL.create(
        drivername="hana+hdbcli",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
    )

    return _execute_query(
        query,
        url,
        {
            "connectTimeout": connection_timeout * 1_000,
            "communicationTimeout": socket_timeout * 1_000,
        },
        "SAP HANA",
        execution_timeout,
        socket_timeout,
    )


def query_mssql(
    sql_path: str | Path,
    user: str,
    password: str,
    host: str,
    driver: str = "ODBC Driver 17 for SQL Server",
    database: str | None = None,
    port: int | None = None,
    connection_timeout: int = 30,
    execution_timeout: int = 120,
    socket_timeout: int = 120,
) -> pd.DataFrame:
    """Ejecuta un archivo SQL en SQL Server y devuelve su resultado."""
    _validate_required_connection_fields(
        {
            "user": str,
            "password": str,
            "host": str,
            "driver": str,
        },
        user=user,
        password=password,
        host=host,
        driver=driver,
    )
    if database is not None:
        _validate_required_connection_fields({"database": str}, database=database)
    if port is not None:
        _validate_required_connection_fields({"port": int}, port=port)
    _validate_timeouts(
        connection_timeout,
        execution_timeout,
        socket_timeout,
    )
    query = _read_sql_file(sql_path)
    url = URL.create(
        drivername="mssql+pyodbc",
        username=user,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"driver": driver},
    )

    return _execute_query(
        query,
        url,
        {"timeout": connection_timeout},
        "SQL Server",
        execution_timeout,
        socket_timeout,
    )
