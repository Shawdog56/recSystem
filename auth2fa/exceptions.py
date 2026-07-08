"""
Excepciones personalizadas del módulo auth2fa.

Cada excepción representa un caso de error específico en el flujo
de verificación en dos pasos, permitiendo que los controladores
manejen cada error de forma granular.
"""


class Auth2FAError(Exception):
    """Excepción base del módulo auth2fa."""

    def __init__(self, message: str = "Error en autenticación 2FA", code: str = "auth2fa_error"):
        self.code = code
        super().__init__(message)


class TokenExpired(Auth2FAError):
    """El código de verificación ha expirado."""

    def __init__(self, message: str = "El código de verificación ha expirado. Solicita uno nuevo."):
        super().__init__(message=message, code="token_expired")


class InvalidToken(Auth2FAError):
    """El código de verificación no es válido."""

    def __init__(self, message: str = "El código de verificación es inválido."):
        super().__init__(message=message, code="invalid_token")


class TokenAlreadyUsed(Auth2FAError):
    """El código de verificación ya fue utilizado."""

    def __init__(self, message: str = "El código de verificación ya fue utilizado."):
        super().__init__(message=message, code="token_already_used")


class EmailSendError(Auth2FAError):
    """Error al enviar el correo electrónico."""

    def __init__(self, message: str = "Error al enviar el correo de verificación. Intenta nuevamente."):
        super().__init__(message=message, code="email_send_error")


class UserNotFound(Auth2FAError):
    """El usuario no existe en el sistema."""

    def __init__(self, message: str = "No se encontró un usuario con ese correo electrónico."):
        super().__init__(message=message, code="user_not_found")
