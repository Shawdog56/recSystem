from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.test import TestCase

from .models import Usuario


class RegisterFlowTest(TestCase):
    """Tests de integración para el flujo de registro + verificación."""

    def _set_reg_session(self, client, code='123456', username='testuser',
                         email='test@example.com', telefono='5512345600'):
        session = client.session
        session['reg_code'] = code
        session['reg_code_expires'] = '2099-12-31T23:59:59+00:00'
        session['reg_data'] = {
            'username': username,
            'password': 'SecurePass123!',
            'nombre': 'Test',
            'apellidos': 'User',
            'telefono': telefono,
            'correo': email,
        }
        session['verify_email'] = email
        session['verify_mode'] = 'registration'
        session.save()

    def test_register_page_serves_form(self):
        """GET /register/ debe renderizar el template."""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/register.html')

    def test_login_page_serves_form(self):
        """GET /login/ debe renderizar el template."""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/login.html')

    def test_verify_page_redirects_if_no_session(self):
        """GET /verify/ sin sesión debe redirigir a /register/."""
        response = self.client.get('/verify/')
        self.assertRedirects(response, '/register/')

    @patch('recluitment.views.send_mail')
    def test_register_stores_data_in_session_and_redirects(
        self, mock_send_mail
    ):
        """POST /register/ guarda en sesión, NO crea usuario aún."""
        response = self.client.post('/register/', {
            'username': 'testuser',
            'password': 'SecurePass123!',
            'nombre': 'Test',
            'apellidos': 'User',
            'telefono': '5512345600',
            'correo': 'test@example.com',
        })

        self.assertRedirects(response, '/verify/')

        # Usuario NO debe existir en BD
        self.assertFalse(Usuario.objects.filter(username='testuser').exists())

        # Datos guardados en sesión
        self.assertEqual(
            self.client.session.get('verify_email'), 'test@example.com'
        )
        self.assertIsNotNone(self.client.session.get('reg_code'))
        self.assertIsNotNone(self.client.session.get('reg_data'))
        mock_send_mail.assert_called_once()

    @patch('recluitment.views.send_mail')
    def test_register_duplicate_username_shows_error(
        self, mock_send_mail
    ):
        """Registro con username duplicado debe mostrar error."""
        Usuario.objects.create(
            username='testuser',
            password='hash',
            nombre='Existente',
            correo='existing@example.com',
            telefono='5512345670',
        )

        response = self.client.post('/register/', {
            'username': 'testuser',
            'password': 'SecurePass123!',
            'nombre': 'Test',
            'correo': 'new@example.com',
            'telefono': '5512345679',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ya está registrado')

    def test_register_without_password_shows_error(self):
        """Registro sin contraseña debe mostrar error."""
        response = self.client.post('/register/', {
            'username': 'testuser',
            'password': '',
            'nombre': 'Test',
            'correo': 'test@example.com',
            'telefono': '5512345600',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'obligatoria')

    def test_verify_valid_code_creates_user(self):
        """Código válido en verify crea el usuario y redirige al home."""
        self._set_reg_session(self.client)

        response = self.client.post('/verify/', {
            'code1': '1', 'code2': '2', 'code3': '3',
            'code4': '4', 'code5': '5', 'code6': '6',
        })

        self.assertRedirects(response, '/')

        # Usuario creado y activo
        user = Usuario.objects.get(username='testuser')
        self.assertTrue(user.enabled)
        self.assertEqual(user.correo, 'test@example.com')
        self.assertTrue(check_password('SecurePass123!', user.password))

    def test_verify_invalid_code_shows_error(self):
        """Código incorrecto muestra error y no crea usuario."""
        self._set_reg_session(self.client)

        response = self.client.post('/verify/', {
            'code1': '0', 'code2': '0', 'code3': '0',
            'code4': '0', 'code5': '0', 'code6': '0',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'incorrecto')
        self.assertFalse(Usuario.objects.filter(username='testuser').exists())

    @patch('recluitment.views.token_service.generate')
    @patch('recluitment.views.email_sender.send_code')
    def test_unverified_user_login_redirects_to_verify(
        self, mock_send_code, mock_generate
    ):
        """Login de usuario sin verificar redirige a /verify/."""
        from django.contrib.auth.hashers import make_password
        mock_generate.return_value.code = '123456'

        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345601',
            enabled=False,
        )

        response = self.client.post('/login/', {
            'correo': 'test@example.com',
            'password': 'SecurePass123!',
        })

        self.assertRedirects(response, '/verify/')

    def test_login_with_verified_user_succeeds(self):
        """Login de usuario verificado debe redirigir al dashboard."""
        from django.contrib.auth.hashers import make_password
        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345602',
            enabled=True,
        )

        response = self.client.post('/login/', {
            'correo': 'test@example.com',
            'password': 'SecurePass123!',
        })

        self.assertRedirects(response, '/dashboard/')

    def test_logout_clears_session(self):
        """Logout debe limpiar la sesión y redirigir a /login/."""
        from django.contrib.auth.hashers import make_password
        user = Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345603',
            enabled=True,
        )

        session = self.client.session
        session['user_id'] = user.id
        session['username'] = user.username
        session.save()

        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')

        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    @patch('recluitment.views.token_service.generate')
    @patch('recluitment.views.email_sender.send_code')
    def test_forgot_password_sends_code_and_redirects(
        self, mock_send_code, mock_generate
    ):
        """POST /forgot-password/ debe enviar código y redirigir a /verify/."""
        from django.contrib.auth.hashers import make_password
        mock_generate.return_value.code = '654321'

        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345604',
            enabled=True,
        )

        response = self.client.post('/forgot-password/', {
            'email': 'test@example.com',
        })

        self.assertRedirects(response, '/verify/')
        self.assertEqual(
            self.client.session.get('verify_mode'), 'password_reset'
        )
        self.assertEqual(
            self.client.session.get('verify_email'), 'test@example.com'
        )

    @patch('recluitment.views.token_service.validate')
    def test_verify_code_for_password_reset_redirects_to_reset_password(
        self, mock_validate
    ):
        """Código válido en modo password_reset redirige a /reset-password/."""
        from django.contrib.auth.hashers import make_password

        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345605',
            enabled=True,
        )

        session = self.client.session
        session['verify_email'] = 'test@example.com'
        session['verify_mode'] = 'password_reset'
        session.save()

        response = self.client.post('/verify/', {
            'code1': '1', 'code2': '2', 'code3': '3',
            'code4': '4', 'code5': '5', 'code6': '6',
        })

        self.assertRedirects(response, '/reset-password/')
        self.assertTrue(
            self.client.session.get('password_reset_verified')
        )

    def test_reset_password_without_verification_redirects(self):
        """GET /reset-password/ sin verificación redirige a /forgot-password/."""
        response = self.client.get('/reset-password/')
        self.assertRedirects(response, '/forgot-password/')

    def test_reset_password_updates_password(self):
        """POST /reset-password/ con sesión verificada cambia la contraseña."""
        from django.contrib.auth.hashers import make_password

        Usuario.objects.create(
            username='testuser',
            password=make_password('OldPass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345606',
            enabled=True,
        )

        session = self.client.session
        session['password_reset_verified'] = True
        session['password_reset_email'] = 'test@example.com'
        session.save()

        response = self.client.post('/reset-password/', {
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        })

        self.assertRedirects(response, '/login/')

        user = Usuario.objects.get(username='testuser')
        self.assertTrue(check_password('NewPass456!', user.password))

    def test_reset_password_passwords_mismatch(self):
        """POST /reset-password/ con passwords distintas muestra error."""
        from django.contrib.auth.hashers import make_password

        Usuario.objects.create(
            username='testuser',
            password=make_password('OldPass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345607',
            enabled=True,
        )

        session = self.client.session
        session['password_reset_verified'] = True
        session['password_reset_email'] = 'test@example.com'
        session.save()

        response = self.client.post('/reset-password/', {
            'new_password': 'NewPass456!',
            'confirm_password': 'DifferentPass!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'no coinciden')
