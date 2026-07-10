"""
Implementación concreta de AbstractTokenService.

Genera códigos de 6 dígitos criptográficamente seguros y maneja
todo el ciclo de vida del token: creación, validación y expiración.
"""

import secrets
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from auth2fa.models import VerificationToken
from auth2fa.exceptions import (
    Auth2FAError,
    InvalidToken,
    TokenExpired,
    TokenAlreadyUsed,
)
from auth2fa.services.interfaces import AbstractTokenService

logger = logging.getLogger(__name__)


class TokenServiceImpl(AbstractTokenService):
    """
    Servicio concreto de generación y validación de tokens.

    SRP: única responsabilidad — gestionar tokens de verificación.
    OCP: extensible vía herencia sin modificar el código cliente.
    """

    def generate(self, user, token_type: str) -> VerificationToken:
        """
        Genera un código de 6 dígitos criptográficamente seguro.

        Flujo:
          1. Invalida tokens previos del mismo tipo para el usuario (evita acumulación).
          2. Genera código de 6 dígitos con secrets.randbelow().
          3. Persiste y retorna el nuevo token.

        Args:
            user: Instancia del modelo User (debe estar persistida en BD).
            token_type: Tipo de token (Type.EMAIL_VERIFICATION o Type.PASSWORD_CHANGE).

        Returns:
            VerificationToken: Token persistido.
        """
        logger.info('Generando token type=%s para user=%s', token_type, user)

        try:
            with transaction.atomic():
                VerificationToken.objects.filter(
                    user=user,
                    type=token_type,
                    is_used=False,
                ).update(is_used=True)

                code = self._generate_code()
                token = VerificationToken.objects.create(
                    user=user,
                    code=code,
                    type=token_type,
                    expires_at=timezone.now() + timedelta(
                        minutes=settings.TOKEN_EXPIRY_MINUTES
                    ),
                )

            logger.info('Token generado exitosamente id=%s', token.pk)
            return token

        except Exception as e:
            logger.error('Error generando token: %s', str(e), exc_info=True)
            raise Auth2FAError('No se pudo generar el código de verificación.') from e

    def validate(self, user, code: str, token_type: str) -> VerificationToken:
        """
        Valida un código de verificación.

        Flujo:
          1. Busca un token activo para user + code + type + is_used=False.
          2. Si no existe → InvalidToken.
          3. Si existe pero expiró → TokenExpired.
          4. Marca como usado y retorna el token.

        Args:
            user: Instancia del modelo User (debe estar persistida en BD).
            code: Código de 6 dígitos a validar.
            token_type: Tipo de token esperado.

        Returns:
            VerificationToken: Token validado y marcado como usado.
        """
        logger.debug('Validando token type=%s para user=%s', token_type, user)

        try:
            with transaction.atomic():
                token = VerificationToken.objects.filter(
                    user=user,
                    code=code,
                    type=token_type,
                    is_used=False,
                ).select_for_update().first()

                if token is None:
                    logger.warning('Token inválido para user=%s code=%s', user, code)
                    raise InvalidToken()

                if token.is_expired:
                    logger.warning('Token expirado id=%s para user=%s', token.pk, user)
                    raise TokenExpired()

                token.is_used = True
                token.save(update_fields=['is_used'])

            logger.info('Token validado exitosamente id=%s', token.pk)
            return token

        except (InvalidToken, TokenExpired):
            raise
        except Exception as e:
            logger.error('Error validando token: %s', str(e), exc_info=True)
            raise Auth2FAError('Error al validar el código.') from e

    def invalidate_previous_tokens(self, user, token_type: str) -> int:
        """
        Invalida todos los tokens no usados de un tipo para un usuario.

        Útil para limpieza antes de generar un nuevo token.

        Args:
            user: Instancia del modelo User (debe estar persistida en BD).
            token_type: Tipo de token a invalidar.

        Returns:
            int: Cantidad de tokens invalidados.
        """
        count = VerificationToken.objects.filter(
            user=user,
            type=token_type,
            is_used=False,
        ).update(is_used=True)

        if count:
            logger.info('Invalidados %d tokens previos type=%s para user=%s', count, token_type, user)

        return count

    def _generate_code(self) -> str:
        """
        Genera un código de N dígitos usando secrets.randbelow para
        garantizar seguridad criptográfica (no predecible).

        Returns:
            str: Código de 6 dígitos con leading zeros.
        """
        max_value = 10 ** settings.TOKEN_LENGTH
        code = secrets.randbelow(max_value)
        return str(code).zfill(settings.TOKEN_LENGTH)
