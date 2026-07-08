"""
Configuración del panel de administración para auth2fa.

Registra el modelo VerificationToken con una vista que permita
buscar, filtrar y gestionar los tokens desde el admin de Django.
"""

from django.contrib import admin

from auth2fa.models import VerificationToken


@admin.register(VerificationToken)
class VerificationTokenAdmin(admin.ModelAdmin):
    """
    Admin para tokens de verificación.

    Proporciona búsqueda por usuario y código, filtros por tipo
    y estado, y ordenamiento por fecha de creación.
    """

    list_display = [
        'user',
        'code',
        'type',
        'is_used',
        'created_at',
        'expires_at',
    ]
    list_filter = [
        'type',
        'is_used',
        'created_at',
    ]
    search_fields = [
        'user__email',
        'user__username',
        'code',
    ]
    readonly_fields = [
        'code',
        'type',
        'created_at',
        'expires_at',
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
