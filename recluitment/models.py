from django.db import models

class Rol(models.Model):
    id = models.BigAutoField(primary_key=True)
    descripcion = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'rol'

class Usuario(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    nombre = models.CharField(max_length=50)
    apellidos = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=15, unique=True)
    correo = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)
    
    last_login = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    @property
    def is_authenticated(self):
        return True

    roles = models.ManyToManyField(
        'Rol', 
        through='UsuarioRol', 
        related_name='usuarios'
    )

    class Meta:
        managed = False
        db_table = 'usuario'

class UsuarioRol(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, db_column='usuario_id')
    rol = models.ForeignKey('Rol', on_delete=models.CASCADE, db_column='rol_id')

    class Meta:
        managed = False
        db_table = 'usuario_rol'
        unique_together = (('usuario', 'rol'),)