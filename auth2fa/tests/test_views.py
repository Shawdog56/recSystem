"""
Tests de integración para los controladores (views) de auth2fa.

Testean el flujo completo request -> servicio -> response usando
mocks para aislar las dependencias externas.
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.contrib.auth import get_user_model

from auth2fa.exceptions import InvalidToken, TokenExpired

User = get_user_model()


class SendCodeViewTest(TestCase):
    """Tests para SendCodeView."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepass123',
        )
        self.url = '/api/auth2fa/send-code/'

    def _post(self, data: dict):
        """Helper para hacer POST con JSON."""
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_successful_send_code(self):
        """Envío exitoso debe retornar 200 con success=True."""
        mock_token_service = MagicMock()
        mock_email_sender = MagicMock()
        mock_token_service.generate.return_value = MagicMock(code='483921')
        mock_email_sender.send_code.return_value = True

        with patch('auth2fa.views.TokenServiceImpl', return_value=mock_token_service), \
             patch('auth2fa.views.EmailSenderImpl', return_value=mock_email_sender):

            response = self._post({
                'email': 'test@example.com',
                'type': 'email_verification',
            })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Código enviado', data['message'])

    def test_missing_email_returns_400(self):
        """Email faltante debe retornar 400."""
        response = self._post({'type': 'email_verification'})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('email', data['errors'])

    def test_invalid_token_type_returns_400(self):
        """Tipo de token inválido debe retornar 400."""
        response = self._post({
            'email': 'test@example.com',
            'type': 'invalid_type',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('type', response.json()['errors'])

    def test_nonexistent_email_returns_404(self):
        """Email no registrado debe retornar 404."""
        response = self._post({
            'email': 'noexiste@example.com',
            'type': 'email_verification',
        })

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])


class VerifyCodeViewTest(TestCase):
    """Tests para VerifyCodeView."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='securepass123',
        )
        self.url = '/api/auth2fa/verify-code/'

    def _post(self, data: dict):
        return self.client.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json',
        )

    def test_successful_verification(self):
        """Verificación exitosa debe retornar 200 con success=True."""
        mock_service = MagicMock()
        mock_service.validate.return_value = MagicMock()

        with patch('auth2fa.views.TokenServiceImpl', return_value=mock_service):
            response = self._post({
                'email': 'test@example.com',
                'code': '483921',
                'type': 'email_verification',
            })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_invalid_code_returns_400(self):
        """Código inválido debe retornar 400."""
        mock_service = MagicMock()
        mock_service.validate.side_effect = InvalidToken()

        with patch('auth2fa.views.TokenServiceImpl', return_value=mock_service):
            response = self._post({
                'email': 'test@example.com',
                'code': '000000',
                'type': 'email_verification',
            })

        self.assertEqual(response.status_code, 400)
        self.assertIn('code', response.json()['errors'])

    def test_expired_code_returns_400(self):
        """Código expirado debe retornar 400."""
        mock_service = MagicMock()
        mock_service.validate.side_effect = TokenExpired()

        with patch('auth2fa.views.TokenServiceImpl', return_value=mock_service):
            response = self._post({
                'email': 'test@example.com',
                'code': '483921',
                'type': 'email_verification',
            })

        self.assertEqual(response.status_code, 400)
        self.assertIn('code', response.json()['errors'])

    def test_validation_errors(self):
        """Errores de validación deben retornar 400."""
        test_cases = [
            ({'code': '483921', 'type': 'email_verification'}, 'email'),
            ({'email': 'test@example.com', 'type': 'email_verification'}, 'code'),
            ({'email': 'test@example.com', 'code': 'abc', 'type': 'email_verification'}, 'code'),
            ({'email': 'test@example.com', 'code': '483921'}, 'type'),
        ]

        for data, expected_error_field in test_cases:
            with self.subTest(data=data):
                response = self._post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_error_field, response.json()['errors'])
