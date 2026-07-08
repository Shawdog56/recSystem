"""
Interfaces abstractas para el módulo auth2fa.

Define contratos que las implementaciones concretas deben cumplir.
Aplicación de:
  - DIP (Dependency Inversion): las vistas dependen de estas abstracciones,
    no de implementaciones concretas.
  - ISP (Interface Segregation): cada interfaz tiene una responsabilidad
    específica y acotada.
  - OCP (Open/Closed): podemos agregar nuevos proveedores de email o
    estrategias de token sin modificar el código cliente.
"""

from abc import ABC, abstractmethod


class AbstractTokenService(ABC):
    """
    Contrato para servicios de generación y validación de tokens.

    Responsabilidad única: gestionar el ciclo de vida del token
    (creación, validación, invalidación).
    """

    @abstractmethod
    def generate(self, user, token_type: str) -> 'VerificationToken':
        """
        Genera un nuevo código de verificación para el usuario.

        Args:
            user: Instancia del modelo User.
            token_type: Tipo de token (Type.EMAIL_VERIFICATION o Type.PASSWORD_CHANGE).

        Returns:
            VerificationToken: Token persistido con el código generado.

        Raises:
            Auth2FAError: Si hay un error en la generación.
        """
        ...

    @abstractmethod
    def validate(self, user, code: str, token_type: str) -> 'VerificationToken':
        """
        Valida un código de verificación.

        Args:
            user: Instancia del modelo User.
            code: Código de 6 dígitos a validar.
            token_type: Tipo de token esperado.

        Returns:
            VerificationToken: Token validado y marcado como usado.

        Raises:
            InvalidToken: Si el código no existe o no corresponde.
            TokenExpired: Si el código expiró.
            TokenAlreadyUsed: Si el código ya fue usado.
        """
        ...


class AbstractEmailSender(ABC):
    """
    Contrato para el envío de correos electrónicos.

    Responsabilidad única: enviar correos con códigos de verificación.
    Permite cambiar de proveedor (Google SMTP, SendGrid, Mailgun, etc.)
    sin modificar el código que lo consume.
    """

    @abstractmethod
    def send_code(self, to_email: str, code: str, token_type: str, user_name: str = '') -> bool:
        """
        Envía un correo con el código de verificación.

        Args:
            to_email: Correo electrónico del destinatario.
            code: Código de verificación de 6 dígitos.
            token_type: Tipo de token (define el mensaje del correo).
            user_name: Nombre del usuario para personalización.

        Returns:
            bool: True si el correo se envió correctamente.

        Raises:
            EmailSendError: Si falla el envío del correo.
        """
        ...
