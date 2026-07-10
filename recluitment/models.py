from django.contrib.auth.hashers import make_password
from django.db import models


class UsuarioManager(models.Manager):
    """Manager compatible con Django Auth para el modelo Usuario."""

    def create_user(self, username, email=None, password=None, **extra_fields):
        """Crea un usuario regular."""
        if not username:
            raise ValueError('El nombre de usuario es obligatorio.')
        user = self.model(
            username=username,
            correo=email or '',
            password=make_password(password) if password else '',
            enabled=True,
            **extra_fields,
        )
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Crea un superusuario (con permisos de admin)."""
        extra_fields.setdefault('nombre', extra_fields.pop('nombre', 'Admin'))
        return self.create_user(username, email, password, **extra_fields)


class Rol(models.Model):
    id = models.BigAutoField(primary_key=True)
    descripcion = models.CharField(max_length=50)

    class Meta:
        managed = True
        db_table = 'rol'

class Usuario(models.Model):
    objects = UsuarioManager()

    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=15, unique=True)
    correo = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)

    roles = models.ManyToManyField(
        'Rol', 
        through='UsuarioRol', 
        related_name='usuarios'
    )

    class Meta:
        managed = True
        db_table = 'usuario'

    # ─── Compatibilidad con Django Auth ───────────────────────────────
    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['username', 'nombre']

    @property
    def email(self):
        """Alias para que auth2fa pueda usar user.email."""
        return self.correo

    @email.setter
    def email(self, value):
        self.correo = value

    @property
    def is_active(self):
        """Alias para is_active → enabled."""
        return self.enabled

    @is_active.setter
    def is_active(self, value):
        self.enabled = value

    def get_full_name(self):
        """Retorna nombre completo (requerido por auth2fa)."""
        parts = [self.nombre, self.apellidos or '']
        return ' '.join(p.strip() for p in parts if p.strip())

    def get_short_name(self):
        return self.nombre

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return f'{self.username} ({self.correo})'

class UsuarioRol(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, db_column='usuario_id')
    rol = models.ForeignKey('Rol', on_delete=models.CASCADE, db_column='rol_id')

    class Meta:
        managed = True
        db_table = 'usuario_rol'
        unique_together = (('usuario', 'rol'),)