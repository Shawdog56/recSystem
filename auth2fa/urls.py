"""
Rutas del módulo auth2fa.

Define los endpoints para el envío y verificación de códigos.
Todas las rutas se montan bajo /api/auth2fa/ desde config/urls.py.
"""

from django.urls import path
from auth2fa.views import SendCodeView, VerifyCodeView

app_name = 'auth2fa'

urlpatterns = [
    path(
        'send-code/',
        SendCodeView.as_view(),
        name='send-code',
    ),
    path(
        'verify-code/',
        VerifyCodeView.as_view(),
        name='verify-code',
    ),
]
