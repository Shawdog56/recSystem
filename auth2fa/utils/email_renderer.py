"""
Utilidad para renderizar plantillas HTML de correos electrónicos.

SRP: única responsabilidad — tomar datos del token y producir
HTML listo para enviar por email.

Permite cambiar el diseño visual de los correos sin tocar la
lógica de envío (OCP).
"""

import logging

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

TEMPLATE_VERIFICATION = 'auth2fa/verification_email.html'


class EmailRenderer:
    """
    Renderiza plantillas HTML para los correos de verificación.

    Uso:
        renderer = EmailRenderer()
        html = renderer.render('483921', 'email_verification', 'Juan')
    """

    def render(self, code: str, token_type: str, user_name: str = '') -> str:
        """
        Renderiza la plantilla HTML del correo con el contexto dado.

        Args:
            code: Código de verificación de 6 dígitos.
            token_type: Tipo de token.
            user_name: Nombre del usuario (opcional).

        Returns:
            str: HTML del correo listo para enviar.
        """
        context = {
            'code': code,
            'token_type': token_type,
            'user_name': user_name or 'Usuario',
            'action_label': self._get_action_label(token_type),
            'expiry_minutes': self._get_expiry_minutes(),
        }

        try:
            html = render_to_string(TEMPLATE_VERIFICATION, context)
            logger.debug('Template renderizado exitosamente')
            return html
        except Exception as e:
            logger.error('Error rendereando template: %s', str(e), exc_info=True)
            return self._fallback_html(code, token_type)

    def _get_action_label(self, token_type: str) -> str:
        """Retorna la etiqueta de acción según el tipo de token."""
        labels = {
            'email_verification': 'Verificar mi correo',
            'password_change': 'Cambiar mi contraseña',
        }
        return labels.get(token_type, 'Verificar')

    def _get_expiry_minutes(self) -> int:
        """Retorna los minutos de expiración desde settings."""
        from django.conf import settings
        return settings.TOKEN_EXPIRY_MINUTES

    def _fallback_html(self, code: str, token_type: str) -> str:
        """
        HTML de respaldo si falla la carga del template.
        Mantiene el sistema funcional aunque la plantilla tenga errores.
        """
        action = self._get_action_label(token_type)
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Código de verificación</h2>
            <p>Tu código para <strong>{action}</strong> es:</p>
            <h1 style="font-size: 36px; letter-spacing: 8px; color: #2563eb;">{code}</h1>
            <p>Este código expira en {self._get_expiry_minutes()} minutos.</p>
        </body>
        </html>
        '''
