from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.test import TestCase
from django.urls import reverse

from .models import Usuario


class RegisterFlowTest(TestCase):
    """Tests de integración para el flujo de registro + verificación."""

    def test_register_page_serves_form(self):
        """GET /register/ debe renderizar el template."""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')

    def test_login_page_serves_form(self):
        """GET /login/ debe renderizar el template."""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_verify_page_redirects_if_no_session(self):
        """GET /verify/ sin sesión debe redirigir a /register/."""
        response = self.client.get('/verify/')
        self.assertRedirects(response, '/register/')

    @patch('recluitment.views.token_service.generate')
    @patch('recluitment.views.email_sender.send_code')
    def test_register_creates_user_and_redirects_to_verify(
        self, mock_send_code, mock_generate
    ):
        """POST /register/ con datos válidos crea usuario inactivo y redirige."""
        mock_generate.return_value.code = '123456'

        response = self.client.post('/register/', {
            'username': 'testuser',
            'password': 'SecurePass123!',
            'nombre': 'Test',
            'apellidos': 'User',
            'telefono': '5512345678',
            'correo': 'test@example.com',
        })

        self.assertRedirects(response, '/verify/')

        # Verificar que el usuario se creó inactivo
        user = Usuario.objects.get(username='testuser')
        self.assertFalse(user.enabled)
        self.assertEqual(user.correo, 'test@example.com')
        self.assertTrue(check_password('SecurePass123!', user.password))

        # Verificar que se generó un token y se envió el email
        mock_generate.assert_called_once()
        mock_send_code.assert_called_once()

    @patch('recluitment.views.token_service.generate')
    @patch('recluitment.views.email_sender.send_code')
    def test_register_duplicate_username_shows_error(
        self, mock_send_code, mock_generate
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
            'telefono': '5512345678',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'obligatoria')

    @patch('recluitment.views.token_service.validate')
    def test_verify_valid_code_activates_user(self, mock_validate):
        """Código válido debe activar al usuario y redirigir al home."""
        user = Usuario.objects.create(
            username='testuser',
            password='hash',
            nombre='Test',
            correo='test@example.com',
            telefono='5512345678',
            enabled=False,
        )

        session = self.client.session
        session['verify_user_id'] = user.id
        session['verify_email'] = user.correo
        session.save()

        response = self.client.post('/verify/', {
            'code1': '1', 'code2': '2', 'code3': '3',
            'code4': '4', 'code5': '5', 'code6': '6',
        })

        self.assertRedirects(response, '/')

        user.refresh_from_db()
        self.assertTrue(user.enabled)

    def test_login_with_unverified_user_redirects_to_verify(self):
        """Login de usuario no verificado debe redirigir a /verify/."""
        from django.contrib.auth.hashers import make_password
        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345678',
            enabled=False,
        )

        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })

        self.assertRedirects(response, '/verify/')

    def test_login_with_verified_user_succeeds(self):
        """Login de usuario verificado debe redirigir al home."""
        from django.contrib.auth.hashers import make_password
        Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345678',
            enabled=True,
        )

        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'SecurePass123!',
        })

        self.assertRedirects(response, '/')

    def test_logout_clears_session(self):
        """Logout debe limpiar la sesión y redirigir a /login/."""
        from django.contrib.auth.hashers import make_password
        user = Usuario.objects.create(
            username='testuser',
            password=make_password('SecurePass123!'),
            nombre='Test',
            correo='test@example.com',
            telefono='5512345678',
            enabled=True,
        )

        # Iniciar sesión
        session = self.client.session
        session['user_id'] = user.id
        session['username'] = user.username
        session.save()

        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')

        # Verificar que la sesión se limpió
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
