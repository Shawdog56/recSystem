"""
Modelo VerificationToken para el módulo auth2fa.

Almacena códigos de verificación de 6 dígitos asociados a un usuario,
con tipo (verificación de email o cambio de contraseña), control de
expiración y estado de uso.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class VerificationToken(models.Model):
    """
    Token de verificación de 6 dígitos para 2FA.

    Responsabilidad única (SRP): almacenar y dar estado a los tokens
    de verificación. La lógica de generación y validación está en
    los servicios, no acá.
    """

    class Type(models.TextChoices):
        """Tipos de token soportados."""
        EMAIL_VERIFICATION = 'email_verification', 'Verificación de correo'
        PASSWORD_CHANGE = 'password_change', 'Cambio de contraseña'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_tokens',
        verbose_name='Usuario',
    )
    code = models.CharField(
        max_length=settings.TOKEN_LENGTH,
        verbose_name='Código',
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        verbose_name='Tipo de token',
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='¿Usado?',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado el',
    )
    expires_at = models.DateTimeField(
        verbose_name='Expira el',
    )

    class Meta:
        verbose_name = 'Token de verificación'
        verbose_name_plural = 'Tokens de verificación'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'code', 'type', 'is_used']),
        ]

    def __str__(self) -> str:
        return f'{self.type} - {self.code} - {self.user}'

    @property
    def is_expired(self) -> bool:
        """Indica si el token ya expiró."""
        return timezone.now() >= self.expires_at

    def save(self, *args, **kwargs):
        """Auto-asigna expires_at si no se proveyó."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(
                minutes=settings.TOKEN_EXPIRY_MINUTES
            )
        super().save(*args, **kwargs)
