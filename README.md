# RecSystem — Liver Talent

Sistema de reclutamiento y bolsa de trabajo construido con Django 6.0.6 y PostgreSQL 15.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 + Django 6.0.6 |
| Base de datos | PostgreSQL 15 (contenedor Docker) |
| Frontend | HTML + CSS + JS (Bootstrap 5.3, Font Awesome) |
| Autenticación | auth2fa (código de 6 dígitos por email) |
| Infraestructura | Docker Compose |
| Tests | `unittest` + `unittest.mock` |

## Requisitos

- Docker y Docker Compose
- Python 3.12+ (para desarrollo local)
- Git

## Inicio rápido

```bash
# 1. Clonar
git clone <repo>
cd recsystem

# 2. Variables de entorno (para SMTP real)
cp .env.example .env   # o crear .env con:
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=tu-correo@gmail.com
# SMTP_PASS=tu-contraseña
# SMTP_SECURE=false

# 3. Levantar servicios
docker compose up -d

# 4. Ejecutar migraciones
docker compose exec web python manage.py migrate

# 5. Verificar
docker compose ps
```

La app queda disponible en `http://localhost:8000`.

## Estructura del proyecto

```
recsystem/
├── config/                  # Configuración Django (settings, urls raíz)
│   ├── settings.py
│   └── urls.py
├── recluitment/             # App principal (usuarios, vacantes)
│   ├── models.py            # Usuario, Rol, UsuarioRol
│   ├── views.py             # Registro, login, vacantes, postulación
│   ├── urls.py              # Rutas del módulo
│   ├── tests.py             # Tests de integración
│   ├── templates/pages/     # Templates HTML
│   │   ├── register.html
│   │   ├── login.html
│   │   ├── verification_code.html
│   │   ├── forgot-password.html
│   │   ├── reset-password.html
│   │   └── vacancy-creation.html
│   ├── static/css/          # Estilos Liver Talent
│   └── migrations/          # Migraciones de BD
├── auth2fa/                 # App de verificación en 2 pasos
│   ├── services/
│   │   ├── token_service.py # Generación y validación de tokens
│   │   └── email_service.py # Envío de correos con HTML template
│   ├── models.py            # VerificationToken
│   └── tests/
├── docker-compose.yml       # PostgreSQL + web Django
├── Dockerfile               # Python 3.12-slim
├── .env                     # Variables de entorno (SMTP)
```
