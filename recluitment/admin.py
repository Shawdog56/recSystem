from django.contrib import admin
from .models import Usuario, Rol, UsuarioRol


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['username', 'nombre', 'correo', 'telefono', 'enabled']
    list_filter = ['enabled']
    search_fields = ['username', 'nombre', 'correo']


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['id', 'descripcion']
    search_fields = ['descripcion']


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'rol']
