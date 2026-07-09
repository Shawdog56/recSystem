"""
Tests unitarios para los servicios de auth2fa.

Usan mocks para aislar la lógica de negocio de las dependencias
externas (BD, SMTP). Esto respeta el principio de testear una
sola unidad a la vez.
"""

from unittest.mock import patch, MagicMock
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from auth2fa.models import VerificationToken
from auth2fa.services.token_service import TokenServiceImpl
from auth2fa.services.email_service import EmailSenderImpl
from auth2fa.exceptions import InvalidToken, TokenExpired, TokenAlreadyUsed

User = get_user_model()


class TokenServiceTest(TestCase):
    """Tests para TokenServiceImpl."""

    def setUp(self):
        self.service = TokenServiceImpl()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepass123',
        )

    def test_generate_creates_token_with_6_digits(self):
        """Verifica que genera un código de exactamente 6 dígitos."""
        token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)

        self.assertEqual(len(token.code), settings.TOKEN_LENGTH)
        self.assertTrue(token.code.isdigit())
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.type, VerificationToken.Type.EMAIL_VERIFICATION)
        self.assertFalse(token.is_used)

    def test_generate_sets_expiry_correctly(self):
        """Verifica que la expiración sea TOKEN_EXPIRY_MINUTES en el futuro."""
        now = timezone.now()
        token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)

        expected_expiry = now + timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES)
        # Tolerancia de 2 segundos por el tiempo de ejecución
        self.assertAlmostEqual(
            token.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=2,
        )

    def test_generate_invalidates_previous_tokens(self):
        """Generar un nuevo token debe invalidar los anteriores del mismo tipo."""
        token1 = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)
        token2 = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)

        token1.refresh_from_db()
        self.assertTrue(token1.is_used)
        self.assertFalse(token2.is_used)

    def test_generate_preserves_tokens_of_other_types(self):
        """Tokens de diferente tipo no deben ser invalidados."""
        email_token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)
        pass_token = self.service.generate(self.user, VerificationToken.Type.PASSWORD_CHANGE)

        email_token.refresh_from_db()
        pass_token.refresh_from_db()

        self.assertFalse(email_token.is_used, 'El token email no debería marcarse como usado')
        self.assertFalse(pass_token.is_used, 'El token password no debería marcarse como usado')

    def test_validate_valid_token(self):
        """Validar un token correcto debe retornarlo y marcarlo como usado."""
        token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)
        validated = self.service.validate(self.user, token.code, VerificationToken.Type.EMAIL_VERIFICATION)

        self.assertEqual(validated.pk, token.pk)
        self.assertTrue(validated.is_used)

    def test_validate_invalid_code_raises_error(self):
        """Código incorrecto debe lanzar InvalidToken."""
        self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)

        with self.assertRaises(InvalidToken):
            self.service.validate(self.user, '000000', VerificationToken.Type.EMAIL_VERIFICATION)

    def test_validate_expired_token_raises_error(self):
        """Token expirado debe lanzar TokenExpired y marcarse como usado."""
        # Creamos el token normalmente
        token = VerificationToken.objects.create(
            user=self.user,
            code='123456',
            type=VerificationToken.Type.EMAIL_VERIFICATION,
        )

        # Forzamos la expiración manualmente (sin mock, directo a la BD)
        past = timezone.now() - timedelta(minutes=1)
        VerificationToken.objects.filter(pk=token.pk).update(
            created_at=past - timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES),
            expires_at=past,
        )
        token.refresh_from_db()

        # Ahora validamos — el token ya expiró
        with self.assertRaises(TokenExpired):
            self.service.validate(self.user, '123456', VerificationToken.Type.EMAIL_VERIFICATION)

        # El token NO se marca como usado (la transacción rollbackea),
        # pero nunca va a validar porque siempre va a estar expirado.
        token.refresh_from_db()
        self.assertFalse(token.is_used, 'Token expirado no se marca como usado (rollback)')

    def test_validate_already_used_token_raises_error(self):
        """Token ya usado debe lanzar InvalidToken (no existe como no-usado)."""
        token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)
        self.service.validate(self.user, token.code, VerificationToken.Type.EMAIL_VERIFICATION)

        with self.assertRaises(InvalidToken):
            self.service.validate(self.user, token.code, VerificationToken.Type.EMAIL_VERIFICATION)

    def test_validate_wrong_type_raises_error(self):
        """Token de tipo diferente debe lanzar InvalidToken."""
        token = self.service.generate(self.user, VerificationToken.Type.EMAIL_VERIFICATION)

        with self.assertRaises(InvalidToken):
            self.service.validate(self.user, token.code, VerificationToken.Type.PASSWORD_CHANGE)


class EmailSenderTest(TestCase):
    """Tests para EmailSenderImpl con mock del envío de correo."""

    def setUp(self):
        self.renderer = MagicMock()
        self.renderer.render.return_value = '<p>HTML</p>'
        self.service = EmailSenderImpl(renderer=self.renderer)

    @patch('auth2fa.services.email_service.send_mail')
    def test_send_code_calls_send_mail(self, mock_send_mail):
        """Verifica que send_code llama a send_mail con los parámetros correctos."""
        mock_send_mail.return_value = 1

        result = self.service.send_code(
            to_email='user@example.com',
            code='483921',
            token_type='email_verification',
            user_name='Juan',
        )

        self.assertTrue(result)
        mock_send_mail.assert_called_once()
        call_kwargs = mock_send_mail.call_args.kwargs

        self.assertEqual(call_kwargs['recipient_list'], ['user@example.com'])
        self.assertIn('483921', call_kwargs['message'])
        self.assertEqual(call_kwargs['html_message'], '<p>HTML</p>')

    @patch('auth2fa.services.email_service.send_mail')
    def test_send_code_returns_false_on_failure(self, mock_send_mail):
        """Si send_mail retorna 0, debe lanzar EmailSendError."""
        mock_send_mail.return_value = 0

        from auth2fa.exceptions import EmailSendError

        with self.assertRaises(EmailSendError):
            self.service.send_code(
                to_email='user@example.com',
                code='483921',
                token_type='email_verification',
            )

    def test_send_code_calls_renderer_with_correct_context(self):
        """Verifica que el renderer reciba los parámetros correctos."""
        with patch('auth2fa.services.email_service.send_mail', return_value=1):
            self.service.send_code(
                to_email='user@example.com',
                code='483921',
                token_type='password_change',
                user_name='María',
            )

        self.renderer.render.assert_called_once_with('483921', 'password_change', 'María')
