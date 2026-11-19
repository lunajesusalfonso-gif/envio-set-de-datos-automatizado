"""
main.py
Proceso: Envío automatizado de sell out (Pre Buen Fin y Buen Fin 2026).

Usa las utilidades de 0-bi-utils (db_extractor, email_dispatcher, log_factory).
Rango del query (src/queries/sell_out.sql): acumulado del 2026-11-09 a ayer,
con tope en el 2026-11-18.

Configuración: ver README.md (.env, consulta SQL y lista de distribución).
Se ejecuta con main.ps1 desde el Programador de tareas (diario 9:30).
"""

import logging
import os
import sys
import zipfile
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parent
UTILS_ROOT = PROJECT_ROOT / "0-bi-utils"
sys.path.insert(0, str(UTILS_ROOT))

from utils.db_extractor import DatabaseAuthenticationError, query_hana  # noqa: E402
from utils.email_dispatcher import send_email  # noqa: E402
from utils.log_factory import get_logger, purge_log_file  # noqa: E402

# ============================================================
# 1. RUTAS Y PARÁMETROS
# ============================================================

DOTENV_PATH = UTILS_ROOT / ".env"
LOG_DIR = PROJECT_ROOT / "log"
SQL_FILE = PROJECT_ROOT / "src" / "queries" / "sell_out.sql"
OUTPUT_FILE = PROJECT_ROOT / "data" / "sell_out.csv"
ZIP_FILE = OUTPUT_FILE.with_suffix(".zip")

# Lista de distribución: config/email_dispatcher/distribution_lists/ (formato: correo,to|cc|cco)
DISTRIBUTION_LIST = "buen_fin.txt"
BODY_TEMPLATE = "buen_fin_body.html"
ASUNTO = "Set de datos Pre Buen Fin y Buen Fin 2026"


def _env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {name}")
    return value


def main() -> None:
    # ========================================================
    # 2. LOG
    # ========================================================
    purge_log_file(LOG_DIR / "hotsale_2026_retail.log", 30)
    logger = get_logger("hotsale_2026_retail", log_dir=LOG_DIR)
    logger.info("Inicio del proceso")

    # ========================================================
    # 3. VARIABLES DE ENTORNO
    # ========================================================
    # Credenciales: .env local (no versionado) o, si no existe, variables de
    # entorno del sistema. Nunca se escriben en código ni en el log.
    if DOTENV_PATH.is_file():
        load_dotenv(DOTENV_PATH, override=True)

    url = make_url(_env("HANA_CONNECTION_STRING"))
    smtp_config = {
        "host": _env("BI_EMAIL_SMTP"),
        "port": _env("BI_EMAIL_PORT"),
        "username": _env("BI_EMAIL_USER"),
        "password": _env("BI_EMAIL_PWD"),
        "use_tls": True,
    }
    logger.info("Variables de entorno cargadas")

    # ========================================================
    # 4. EJECUTAR CONSULTA SQL
    # ========================================================
    try:
        df = query_hana(
            sql_path=SQL_FILE,
            user=url.username,
            password=url.password,
            host=url.host,
            port=url.port,
            database=url.database,
            connection_timeout=10,
            execution_timeout=600,
            socket_timeout=600,
        )
    except DatabaseAuthenticationError:
        logger.error("HANA rechazó las credenciales configuradas")
        raise

    logger.info("Consulta completada: %s filas", len(df))
    if df.empty:
        logger.error("La consulta no regresó filas; no se envía el correo")
        raise SystemExit(1)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info("Archivo guardado: %s", OUTPUT_FILE.name)

    with zipfile.ZipFile(ZIP_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(OUTPUT_FILE, arcname=OUTPUT_FILE.name)
    logger.info(
        "Archivo comprimido: %s (%.1f MB -> %.1f MB)",
        ZIP_FILE.name,
        OUTPUT_FILE.stat().st_size / 1_048_576,
        ZIP_FILE.stat().st_size / 1_048_576,
    )

    # ========================================================
    # 5. ENVIAR CORREO (firma con logo embebido)
    # ========================================================
    response = send_email(
        smtp_config=smtp_config,
        project_root=PROJECT_ROOT,
        distribution_list=DISTRIBUTION_LIST,
        subject=ASUNTO,
        template_name="default.html",
        body_template_name=BODY_TEMPLATE,
        # MIME explícito: en Windows mimetypes puede resolver .zip como x-zip-compressed
        attachments=[{"path": ZIP_FILE, "maintype": "application", "subtype": "zip"}],
    )
    logger.info(
        "Correo enviado correctamente a %s destinatarios",
        response["recipients_count"],
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Deja el error en el log para revisarlo después de la ejecución programada
        logging.getLogger("hotsale_2026_retail").exception("El proceso terminó con error")
        raise
