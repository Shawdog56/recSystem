from django.db import migrations

def populate_initial_data(apps, schema_editor):
    # Fetch models from the historical app registry
    Usuario = apps.get_model('recluitment', 'Usuario')
    Rol = apps.get_model('recluitment', 'Rol')
    UsuarioRol = apps.get_model('recluitment', 'UsuarioRol')

    # 1. Create Roles
    # By assigning them to variables, we don't need to hardcode IDs (1, 2, 3) later
    rol_reclutador = Rol.objects.create(descripcion='ROLE_RECLUTADOR')
    rol_aspirante = Rol.objects.create(descripcion='ROLE_ASPIRANTE')
    rol_admin = Rol.objects.create(descripcion='ROLE_ADMIN')

    # 2. Create the User
    user_shawdog = Usuario.objects.create(
        username='shawdog',
        password='pbkdf2_sha256$1200000$Okg6cOJr9FRpvrJtkwM7PL$ZSMKTthy/5kT/THVq986v/H9E3u1iifFUEHV0rXjVvM=',
        nombre='Admin',
        telefono='5512345678',
        correo='admin@example.com',
        enabled=True,
        last_login=None,
        is_active=True,
        is_staff=False,
        is_superuser=False
    )

    # 3. Assign Roles in the relationship table
    # This matches your INSERT INTO usuario_rol statements perfectly
    UsuarioRol.objects.create(usuario=user_shawdog, rol=rol_admin)
    UsuarioRol.objects.create(usuario=user_shawdog, rol=rol_aspirante)
    UsuarioRol.objects.create(usuario=user_shawdog, rol=rol_reclutador)


def reverse_initial_data(apps, schema_editor):
    # Optional: Logic to delete the data if you ever run `manage.py migrate recluitment 0001`
    Usuario = apps.get_model('recluitment', 'Usuario')
    Rol = apps.get_model('recluitment', 'Rol')
    
    Usuario.objects.filter(username='shawdog').delete()
    Rol.objects.filter(descripcion__in=['ROLE_RECLUTADOR', 'ROLE_ASPIRANTE', 'ROLE_ADMIN']).delete()


class Migration(migrations.Migration):

    dependencies = [
        # This ensures your tables are created before this script runs.
        # Ensure '0001_initial' matches the actual name of your first migration file.
        ('recluitment', '0001_initial'), 
    ]

    operations = [
        migrations.RunPython(populate_initial_data, reverse_code=reverse_initial_data),
    ]