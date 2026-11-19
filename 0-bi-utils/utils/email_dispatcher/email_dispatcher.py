"""Construcción y envío de correos mediante SMTP."""

from __future__ import annotations

import mimetypes
import re
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RECIPIENT_TYPES = {"to", "cc", "cco"}
_CONFIG_DIRECTORY_ERROR = "No existe la carpeta config en la raíz del proyecto"


def _initialize_config_structure(project_root: str | Path) -> Path:
    """Valida config y crea la estructura administrada por email_dispatcher."""
    config_dir = Path(project_root).resolve() / "config"
    if not config_dir.is_dir():
        raise FileNotFoundError(_CONFIG_DIRECTORY_ERROR)

    email_config_dir = config_dir / "email_dispatcher"
    distribution_lists_dir = email_config_dir / "distribution_lists"
    templates_dir = email_config_dir / "templates"
    body_templates_dir = email_config_dir / "body_template"

    distribution_lists_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)
    body_templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "assets").mkdir(exist_ok=True)

    example_distribution = distribution_lists_dir / "example.txt"
    if not example_distribution.exists():
        example_distribution.write_text(
            "example@example.com,to\n",
            encoding="utf-8",
        )

    example_template = templates_dir / "example.html"
    if not example_template.exists():
        example_template.write_text(
            "<!DOCTYPE html>\n"
            '<html lang="es">\n'
            "<body>\n"
            "    {{ body }}\n"
            "</body>\n"
            "</html>\n",
            encoding="utf-8",
        )

    example_body = body_templates_dir / "example_body.html"
    if not example_body.exists():
        example_body.write_text(
            "<p>Este es un cuerpo de correo de ejemplo.</p>\n",
            encoding="utf-8",
        )

    return email_config_dir


def _validate_smtp_config(smtp_config: dict[str, Any]) -> tuple[str, int, str, str, bool]:
    """Valida y normaliza la configuración antes de acceder a archivos o red."""
    if not smtp_config.get("password"):
        raise ValueError("Falta contraseña en la configuración de conexión")
    if smtp_config.get("port") in (None, ""):
        raise ValueError("Falta puerto en la configuración de conexión")

    for field in ("host", "username"):
        if not smtp_config.get(field):
            raise ValueError(f"Faltan elementos para la conexión: {field}")

    port_value = smtp_config["port"]
    if isinstance(port_value, bool):
        raise ValueError("El puerto debe ser un número entero válido")
    try:
        port = int(port_value)
    except (TypeError, ValueError) as error:
        raise ValueError("El puerto debe ser un número entero válido") from error

    return (
        str(smtp_config["host"]),
        port,
        str(smtp_config["username"]),
        str(smtp_config["password"]),
        bool(smtp_config.get("use_tls", True)),
    )


def _parse_distribution_list(path: str | Path) -> tuple[list[str], list[str], list[str]]:
    """Lee el CSV y clasifica los destinatarios conservando su orden."""
    recipients: dict[str, list[str]] = {"to": [], "cc": [], "cco": []}

    with Path(path).open("r", encoding="utf-8-sig") as distribution_file:
        for line_number, raw_line in enumerate(distribution_file, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            fields = [field.strip() for field in line.split(",")]
            if len(fields) != 2:
                raise ValueError(f"Formato inválido en la línea {line_number}")

            email_address, recipient_type = fields
            if not _EMAIL_PATTERN.fullmatch(email_address):
                raise ValueError(f"Correo inválido en la línea {line_number}")

            recipient_type = recipient_type.lower()
            if recipient_type not in _RECIPIENT_TYPES:
                raise ValueError(
                    f"Tipo de envío no permitido en la línea {line_number}"
                )
            recipients[recipient_type].append(email_address)

    return recipients["to"], recipients["cc"], recipients["cco"]


def _load_html(
    email_config_dir: Path,
    template_name: str,
    body_template_name: str,
) -> tuple[str, bytes]:
    """Carga la plantilla solicitada o default.html y la firma institucional."""
    templates_dir = email_config_dir / "templates"
    requested_template = templates_dir / (template_name or "default.html")
    template_path = (
        requested_template
        if requested_template.is_file()
        else templates_dir / "default.html"
    )
    template_content = template_path.read_text(encoding="utf-8")

    body_template_path = email_config_dir / "body_template" / body_template_name
    rendered_body = body_template_path.read_text(encoding="utf-8")

    signature_path = templates_dir / "assets" / "signature_logo.png"
    signature_bytes = signature_path.read_bytes()
    return template_content.replace("{{ body }}", rendered_body), signature_bytes


def _normalize_attachments(
    attachments: list[str | Path | dict[str, Any]] | None,
) -> list[tuple[Path, str, str]]:
    """Verifica todos los adjuntos y resuelve sus tipos MIME antes del ensamble."""
    normalized: list[tuple[Path, str, str]] = []

    for attachment in attachments or []:
        if isinstance(attachment, dict):
            path = Path(attachment["path"])
            maintype = str(attachment["maintype"])
            subtype = str(attachment["subtype"])
        else:
            path = Path(attachment)
            mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            maintype, subtype = mime_type.split("/", maxsplit=1)

        if not path.exists():
            raise FileNotFoundError(path)
        if not path.is_file():
            raise FileNotFoundError(path)
        normalized.append((path, maintype, subtype))

    return normalized


def _build_message(
    sender: str,
    to_addrs: list[str],
    cc_addrs: list[str],
    subject: str,
    html_content: str,
    signature_bytes: bytes,
    attachments: list[tuple[Path, str, str]],
) -> EmailMessage:
    """Ensambla el contenido HTML, la firma CID y los adjuntos del mensaje."""
    message = EmailMessage()
    message["From"] = sender
    if to_addrs:
        message["To"] = ", ".join(to_addrs)
    if cc_addrs:
        message["Cc"] = ", ".join(cc_addrs)
    message["Subject"] = subject

    message.set_content("")
    message.add_alternative(html_content, subtype="html")
    html_part = message.get_payload()[-1]
    html_part.add_related(
        signature_bytes,
        maintype="image",
        subtype="png",
        cid="<signature_logo>",
        filename="signature_logo.png",
        disposition="inline",
    )

    for path, maintype, subtype in attachments:
        message.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=path.name,
        )

    return message


def send_email(
    smtp_config: dict,
    project_root: str | Path,
    distribution_list: str | Path = "bi.csv",
    subject: str = "",
    template_name: str = "default.html",
    body_template_name: str = "example_body.html",
    attachments: list[str | Path | dict] | None = None,
) -> dict:
    """Construye, despacha el correo y devuelve el resumen de la operación."""
    host, port, username, password, use_tls = _validate_smtp_config(smtp_config)
    email_config_dir = _initialize_config_structure(project_root)

    distribution_path = Path(distribution_list)
    if not distribution_path.is_absolute():
        distribution_path = email_config_dir / "distribution_lists" / distribution_path

    to_addrs, cc_addrs, cco_addrs = _parse_distribution_list(distribution_path)
    normalized_attachments = _normalize_attachments(attachments)
    html_content, signature_bytes = _load_html(
        email_config_dir,
        template_name,
        body_template_name,
    )
    message = _build_message(
        username,
        to_addrs,
        cc_addrs,
        subject,
        html_content,
        signature_bytes,
        normalized_attachments,
    )
    all_recipients = to_addrs + cc_addrs + cco_addrs

    smtp_class = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_class(host, port) as smtp:
        if use_tls and port != 465:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message, to_addrs=all_recipients)

    return {"status": "success", "recipients_count": len(all_recipients)}


__all__ = ["send_email"]
