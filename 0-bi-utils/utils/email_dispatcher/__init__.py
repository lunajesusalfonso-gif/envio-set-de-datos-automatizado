"""API pública de la utilidad de envío de correos."""

from .email_dispatcher import send_email

__all__ = ["send_email"]
