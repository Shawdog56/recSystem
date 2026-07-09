"""
Endpoints:
  - POST /api/auth2fa/send-code/   -> Envía código de verificación
  - POST /api/auth2fa/verify-code/ -> Valida código de verificación
"""

import json
import logging

from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from auth2fa.exceptions import (
    Auth2FAError,
    InvalidToken,
    TokenExpired,
    TokenAlreadyUsed,
    EmailSendError,
    UserNotFound,
)
from auth2fa.services.token_service import TokenServiceImpl
from auth2fa.services.email_service import EmailSenderImpl
from auth2fa.services.interfaces import AbstractTokenService, AbstractEmailSender

User = get_user_model()
logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class SendCodeView(View):
    """
    Controlador para enviar un código de verificación al email del usuario.

    POST /api/auth2fa/send-code/
    Body: { "email": "...", "type": "email_verification" }
    """

    def __init__(self, *args, **kwargs):
        """
        Inyección de dependencias (DIP).

        Por defecto usa implementaciones concretas, pero en tests
        podemos inyectar mocks/stubs.
        """
        self.token_service: AbstractTokenService = kwargs.pop(
            'token_service', TokenServiceImpl()
        )
        self.email_sender: AbstractEmailSender = kwargs.pop(
            'email_sender', EmailSenderImpl()
        )
        super().__init__(*args, **kwargs)

    def post(self, request):
        try:
            data = self._parse_body(request)
            email = data.get('email', '').strip().lower()
            token_type = data.get('type', '')

            # Validación de entrada
            errors = self._validate_input(email, token_type)
            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            # Buscar usuario
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse(
                    {'success': False, 'errors': {'email': 'No existe una cuenta con este correo.'}},
                    status=404,
                )

            # 1. Generar token
            token = self.token_service.generate(user, token_type)

            # 2. Enviar correo
            self.email_sender.send_code(
                to_email=email,
                code=token.code,
                token_type=token_type,
                user_name=user.get_full_name() or user.username,
            )

            return JsonResponse({
                'success': True,
                'message': f'Codigo enviado a {email}.',
            })

        except Auth2FAError as e:
            return JsonResponse({'success': False, 'errors': {'general': str(e)}}, status=500)
        except Exception as e:
            logger.error('Error inesperado en SendCodeView: %s', str(e), exc_info=True)
            return JsonResponse(
                {'success': False, 'errors': {'general': 'Error interno del servidor.'}},
                status=500,
            )

    def _parse_body(self, request):
        """Extrae el body JSON de la request."""
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            return {}

    def _validate_input(self, email: str, token_type: str) -> dict:
        """Valida los campos de entrada."""
        errors = {}

        if not email:
            errors['email'] = 'El correo es obligatorio.'

        if not token_type:
            errors['type'] = 'El tipo de token es obligatorio.'
        elif token_type not in ('email_verification', 'password_change'):
            errors['type'] = 'Tipo de token inválido.'

        return errors


@method_decorator(csrf_exempt, name='dispatch')
class VerifyCodeView(View):
    """
    Controlador para validar un código de verificación.

    POST /api/auth2fa/verify-code/
    Body: { "email": "...", "code": "483921", "type": "email_verification" }
    """

    def __init__(self, *args, **kwargs):
        self.token_service: AbstractTokenService = kwargs.pop(
            'token_service', TokenServiceImpl()
        )
        super().__init__(*args, **kwargs)

    def post(self, request):
        try:
            data = self._parse_body(request)
            email = data.get('email', '').strip().lower()
            code = data.get('code', '').strip()
            token_type = data.get('type', '')

            # Validación de entrada
            errors = self._validate_input(email, code, token_type)
            if errors:
                return JsonResponse({'success': False, 'errors': errors}, status=400)

            # Buscar usuario
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return JsonResponse(
                    {'success': False, 'errors': {'email': 'No existe una cuenta con este correo.'}},
                    status=404,
                )

            # Validar token
            self.token_service.validate(user, code, token_type)

            return JsonResponse({
                'success': True,
                'message': 'Código verificado correctamente.',
            })

        except InvalidToken as e:
            return JsonResponse({'success': False, 'errors': {'code': str(e)}}, status=400)
        except TokenExpired as e:
            return JsonResponse({'success': False, 'errors': {'code': str(e)}}, status=400)
        except TokenAlreadyUsed as e:
            return JsonResponse({'success': False, 'errors': {'code': str(e)}}, status=400)
        except Auth2FAError as e:
            return JsonResponse({'success': False, 'errors': {'general': str(e)}}, status=500)
        except Exception as e:
            logger.error('Error inesperado en VerifyCodeView: %s', str(e), exc_info=True)
            return JsonResponse(
                {'success': False, 'errors': {'general': 'Error interno del servidor.'}},
                status=500,
            )

    def _parse_body(self, request):
        try:
            return json.loads(request.body)
        except (json.JSONDecodeError, AttributeError):
            return {}

    def _validate_input(self, email: str, code: str, token_type: str) -> dict:
        errors = {}

        if not email:
            errors['email'] = 'El correo es obligatorio.'

        if not code:
            errors['code'] = 'El código es obligatorio.'
        elif not (len(code) == 6 and code.isdigit()):
            errors['code'] = 'El código debe tener 6 dígitos numéricos.'

        if not token_type:
            errors['type'] = 'El tipo de token es obligatorio.'
        elif token_type not in ('email_verification', 'password_change'):
            errors['type'] = 'Tipo de token inválido.'

        return errors
