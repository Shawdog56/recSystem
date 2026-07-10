# recluitment/backends.py
from django.contrib.auth.backends import ModelBackend
from .models import Usuario

class IgnoreLastLoginBackend(ModelBackend):
    def user_can_authenticate(self, user):
        # We bypass the default check that requires last_login
        return True

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None