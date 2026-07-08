"""
Implementación concreta de AbstractEmailSender.

Envía correos electrónicos con códigos de verificación usando
Google SMTP (o cualquier servidor SMTP configurado) a través
de django.core.mail.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from auth2fa.exceptions import EmailSendError
from auth2fa.services.interfaces import AbstractEmailSender
from auth2fa.utils.email_renderer import EmailRenderer

logger = logging.getLogger(__name__)


class EmailSenderImpl(AbstractEmailSender):
    """
    Envío de correos vía SMTP (Google SMTP por defecto).

    SRP: única responsabilidad — enviar correos con códigos de verificación.
    OCP: cambia el backend SMTP desde settings.py, no desde el código.
    DIP: el controlador inyecta esta dependencia, no la crea internamente.
    """

    def __init__(self, renderer: EmailRenderer | None = None):
        """
        Args:
            renderer: Inyectable para renderizar templates de email.
                      Si no se provee, usa EmailRenderer por defecto.
        """
        self.renderer = renderer or EmailRenderer()

    def send_code(
        self,
        to_email: str,
        code: str,
        token_type: str,
        user_name: str = '',
    ) -> bool:
        """
        Envía el código de verificación al destinatario.

        Args:
            to_email: Correo del destinatario.
            code: Código de 6 dígitos.
            token_type: Tipo de token (define el asunto y mensaje).
            user_name: Nombre del usuario (opcional, para personalizar).

        Returns:
            bool: True si se envió correctamente.

        Raises:
            EmailSendError: Si falla el envío.
        """
        subject = self._get_subject(token_type)
        html_message = self.renderer.render(code, token_type, user_name)
        plain_message = self._get_plain_message(code, token_type)

        logger.info('Enviando correo a=%s type=%s', to_email, token_type)

        try:
            sent_count = send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
            )

            if sent_count == 0:
                logger.error('No se pudo enviar el correo a=%s (sent_count=0)', to_email)
                raise EmailSendError()

            logger.info('Correo enviado exitosamente a=%s', to_email)
            return True

        except EmailSendError:
            raise
        except Exception as e:
            logger.error('Error enviando correo a=%s: %s', to_email, str(e), exc_info=True)
            raise EmailSendError() from e

    def _get_subject(self, token_type: str) -> str:
        """Retorna el asunto del correo según el tipo de token."""
        subjects = {
            'email_verification': settings.VERIFICATION_EMAIL_SUBJECT,
            'password_change': settings.PASSWORD_CHANGE_EMAIL_SUBJECT,
        }
        return subjects.get(token_type, 'Código de verificación')

    def _get_plain_message(self, code: str, token_type: str) -> str:
        """Retorna versión texto plano del mensaje."""
        messages = {
            'email_verification': (
                f'Tu código de verificación es: {code}\n'
                f'Este código expira en {settings.TOKEN_EXPIRY_MINUTES} minutos.\n\n'
                'Si no solicitaste este código, ignora este mensaje.'
            ),
            'password_change': (
                f'Tu código para cambiar la contraseña es: {code}\n'
                f'Este código expira en {settings.TOKEN_EXPIRY_MINUTES} minutos.\n\n'
                'Si no solicitaste este cambio, ignora este mensaje.'
            ),
        }
        return messages.get(
            token_type,
            f'Tu código de verificación es: {code}',
        )
