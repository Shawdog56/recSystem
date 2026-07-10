import logging

from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect, render

from auth2fa.exceptions import InvalidToken, TokenExpired
from auth2fa.models import VerificationToken
from auth2fa.services.email_service import EmailSenderImpl
from auth2fa.services.token_service import TokenServiceImpl

from .models import Usuario

logger = logging.getLogger(__name__)
token_service = TokenServiceImpl()
email_sender = EmailSenderImpl()


# ─── Home ──────────────────────────────────────────────────────────────────


def home(request):
    return render(request, 'index.html')


def hello_world(request):
    return home(request)


def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('pages_login')
    return render(request, 'dashboard.html')


# ─── Registro ──────────────────────────────────────────────────────────────


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        correo = request.POST.get('correo', '').strip().lower()

        # ── Validaciones básicas ────────────────────────────────────────
        errors = []
        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        if not password:
            errors.append('La contraseña es obligatoria.')
        if not correo:
            errors.append('El correo electrónico es obligatorio.')

        if Usuario.objects.filter(username=username).exists():
            errors.append('El nombre de usuario ya está registrado.')
        if Usuario.objects.filter(correo=correo).exists():
            errors.append('El correo electrónico ya está registrado.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'pages/register.html')

        # ── Crear usuario (inactivo hasta verificar email) ──────────────
        user = Usuario.objects.create(
            username=username,
            password=make_password(password),
            nombre=nombre,
            apellidos=apellidos or None,
            telefono=telefono,
            correo=correo,
            enabled=False,
        )

        # ── Generar y enviar código de verificación ─────────────────────
        try:
            token = token_service.generate(
                user, VerificationToken.Type.EMAIL_VERIFICATION
            )
            email_sender.send_code(
                to_email=correo,
                code=token.code,
                token_type=VerificationToken.Type.EMAIL_VERIFICATION,
                user_name=f'{nombre} {apellidos}'.strip() or username,
            )
        except Exception as e:
            logger.error('Error al enviar código de verificación: %s', e)
            # El usuario se creó pero no se pudo enviar el email
            user.delete()
            messages.error(
                request,
                'Error al enviar el código de verificación. Intenta de nuevo.',
            )
            return render(request, 'pages/register.html')

        # Guardamos el ID en sesión para el paso de verificación
        request.session['verify_user_id'] = user.id
        request.session['verify_email'] = correo

        messages.success(
            request,
            f'Registro exitoso. Hemos enviado un código de 6 dígitos a {correo}.',
        )
        return redirect('/verify/')

    return render(request, 'pages/register.html')


# ─── Verificación de email ────────────────────────────────────────────────


def verify(request):
    """Muestra y procesa el formulario de verificación de código."""
    user_id = request.session.get('verify_user_id')
    email = request.session.get('verify_email')

    if not user_id or not email:
        messages.warning(request, 'Debes registrarte primero.')
        return redirect('/register/')

    if request.method == 'POST':
        # Los 6 inputs individuales se concatenan
        code_parts = [
            request.POST.get(f'code{i}', '') for i in range(1, 7)
        ]
        code = ''.join(code_parts)

        if not code or len(code) != 6 or not code.isdigit():
            messages.error(request, 'El código debe tener 6 dígitos numéricos.')
            return render(request, 'pages/verification_code.html', {'email': email})

        try:
            user = Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('/register/')

        try:
            token_service.validate(
                user, code, VerificationToken.Type.EMAIL_VERIFICATION
            )
        except InvalidToken:
            messages.error(request, 'El código ingresado es incorrecto.')
            return render(request, 'pages/verification_code.html', {'email': email})
        except TokenExpired:
            messages.error(
                request,
                'El código ha expirado. Solicita uno nuevo.',
            )
            return render(request, 'pages/verification_code.html', {'email': email})

        # Código válido → activar usuario
        user.enabled = True
        user.save(update_fields=['enabled'])

        # Limpiar sesión de verificación
        request.session.pop('verify_user_id', None)
        request.session.pop('verify_email', None)

        # Iniciar sesión automáticamente
        request.session['user_id'] = user.id
        request.session['username'] = user.username

        messages.success(request, '¡Correo verificado exitosamente!')
        return redirect('/')

    return render(request, 'pages/verification_code.html', {'email': email})


# ─── Reenviar código de verificación ──────────────────────────────────────


def resend_code(request):
    """Reenvía el código de verificación al email en sesión."""
    user_id = request.session.get('verify_user_id')
    email = request.session.get('verify_email')

    if not user_id or not email:
        messages.warning(request, 'No hay verificación pendiente.')
        return redirect('/register/')

    try:
        user = Usuario.objects.get(pk=user_id)
    except Usuario.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('/register/')

    try:
        token = token_service.generate(
            user, VerificationToken.Type.EMAIL_VERIFICATION
        )
        email_sender.send_code(
            to_email=email,
            code=token.code,
            token_type=VerificationToken.Type.EMAIL_VERIFICATION,
            user_name=user.get_full_name() or user.username,
        )
        messages.success(request, f'Se ha reenviado el código a {email}.')
    except Exception as e:
        logger.error('Error al reenviar código: %s', e)
        messages.error(request, 'Error al reenviar el código. Intenta de nuevo.')

    return redirect('/verify/')


# ─── Inicio de sesión ─────────────────────────────────────────────────────


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        try:
            user = Usuario.objects.get(username=username)

            if not check_password(password, user.password):
                messages.error(request, 'Credenciales inválidas.')
                return render(request, 'pages/login.html')

            if not user.enabled:
                # El usuario no ha verificado su email
                request.session['verify_user_id'] = user.id
                request.session['verify_email'] = user.correo

                # Reenviar código automáticamente
                try:
                    token = token_service.generate(
                        user, VerificationToken.Type.EMAIL_VERIFICATION
                    )
                    email_sender.send_code(
                        to_email=user.correo,
                        code=token.code,
                        token_type=VerificationToken.Type.EMAIL_VERIFICATION,
                        user_name=user.get_full_name() or user.username,
                    )
                except Exception as e:
                    logger.error('Error al enviar código en login: %s', e)

                messages.warning(
                    request,
                    'Tu cuenta no está verificada. '
                    'Hemos enviado un nuevo código a tu correo.',
                )
                return redirect('/verify/')

            # Login exitoso
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['roles'] = list(user.roles.values_list('descripcion', flat=True))
            messages.success(request, f'Bienvenido, {user.nombre}!')
            return redirect('/')

        except Usuario.DoesNotExist:
            messages.error(request, 'Credenciales inválidas.')

    return render(request, 'pages/login.html')


# ─── Cierre de sesión ─────────────────────────────────────────────────────


def logout_view(request):
    request.session.flush()
    messages.info(request, 'Sesión cerrada.')
    return redirect('/login/')


# ─── Recuperar contraseña ─────────────────────────────────────────────────


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'El correo es obligatorio.')
            return render(request, 'pages/forgot-password.html')

        try:
            user = Usuario.objects.get(correo=email)
        except Usuario.DoesNotExist:
            # No revelar si el usuario existe o no (seguridad)
            messages.success(
                request,
                'Si el correo existe en nuestro sistema, recibirás instrucciones.',
            )
            return render(request, 'pages/forgot-password.html')

        try:
            token = token_service.generate(
                user, VerificationToken.Type.PASSWORD_CHANGE
            )
            email_sender.send_code(
                to_email=email,
                code=token.code,
                token_type=VerificationToken.Type.PASSWORD_CHANGE,
                user_name=user.get_full_name() or user.username,
            )
        except Exception as e:
            logger.error('Error al enviar código de recuperación: %s', e)

        messages.success(
            request,
            'Si el correo existe en nuestro sistema, recibirás instrucciones.',
        )

    return render(request, 'pages/forgot-password.html')
