from django.apps import AppConfig


class Auth2FaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth2fa'
    verbose_name = 'Autenticación en dos pasos (2FA)'
