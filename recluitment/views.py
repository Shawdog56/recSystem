import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from auth2fa.exceptions import InvalidToken, TokenExpired
from auth2fa.models import VerificationToken
from auth2fa.services.email_service import EmailSenderImpl
from auth2fa.services.token_service import TokenServiceImpl

from .models import Usuario

logger = logging.getLogger(__name__)
token_service = TokenServiceImpl()
email_sender = EmailSenderImpl()

TOKEN_LIFETIME_MINUTES = 10


def _gen_code() -> str:
    return str(secrets.randbelow(10**6)).zfill(6)


def _send_code_email(to_email: str, code: str, user_name: str) -> None:
    subject = 'Código de verificación — Recruitment System'
    plain_message = (
        f'Hola {user_name},\n\n'
        f'Tu código de verificación es:\n\n'
        f'   {code}\n\n'
        f'Este código expira en {TOKEN_LIFETIME_MINUTES} minutos.\n\n'
        f'Si no solicitaste este código, ignora este mensaje.'
    )
    context = {
        'code': code,
        'user_name': user_name or 'Usuario',
        'action_label': 'Verificar mi correo',
        'expiry_minutes': TOKEN_LIFETIME_MINUTES,
    }
    html_message = render_to_string('auth2fa/verification_email.html', context)
    send_mail(subject, plain_message, None, [to_email], html_message=html_message)


# ─── Home ──────────────────────────────────────────────────────────────────


def home(request):
    return render(request, 'index.html')


def hello_world(request):
    return home(request)


def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('pages_login')
    return render(request, 'dashboard.html')


# ─── Registro (el usuario NO se crea hasta validar el código) ─────────────


def register(request):
    # ── Detectar verificación pendiente en GET ──────────────────────
    pending_email = request.session.get('verify_email')
    pending_mode = request.session.get('verify_mode')

    if request.method == 'GET' and request.session.get('reg_data') is not None:
        return redirect('/verify/')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        correo = request.POST.get('correo', '').strip().lower()

        errors = []
        if not username:
            errors.append('El nombre de usuario es obligatorio.')
        if not password:
            errors.append('La contraseña es obligatoria.')
        if not correo:
            errors.append('El correo electrónico es obligatorio.')

        # ── Si el email ya tiene verificación pendiente, reenviar código ──
        has_pending = (
            pending_email == correo
            and pending_mode == 'registration'
            and request.session.get('reg_data') is not None
        )
        if not has_pending:
            if Usuario.objects.filter(username=username).exists():
                errors.append('El nombre de usuario ya está registrado.')
            if Usuario.objects.filter(correo=correo).exists():
                errors.append('El correo electrónico ya está registrado.')
            if Usuario.objects.filter(telefono=telefono).exists():
                errors.append('El número de teléfono ya está registrado.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'pages/register.html')

        code = _gen_code()
        user_name = f'{nombre} {apellidos}'.strip() or username

        try:
            _send_code_email(correo, code, user_name)
        except Exception as e:
            logger.error('Error al enviar código de verificación: %s', e)
            messages.error(
                request,
                'Error al enviar el código de verificación. Intenta de nuevo.',
            )
            return render(request, 'pages/register.html')

        request.session['reg_code'] = code
        request.session['reg_code_expires'] = (
            timezone.now() + timedelta(minutes=TOKEN_LIFETIME_MINUTES)
        ).isoformat()
        request.session['reg_data'] = {
            'username': username,
            'password': password,
            'nombre': nombre,
            'apellidos': apellidos,
            'telefono': telefono,
            'correo': correo,
        }
        request.session['verify_email'] = correo
        request.session['verify_mode'] = 'registration'

        if has_pending:
            messages.success(
                request,
                f'Hemos reenviado un nuevo código a {correo}.',
            )
        else:
            messages.success(
                request,
                f'Hemos enviado un código de 6 dígitos a {correo}.'
                ' Verifícalo para completar tu registro.',
            )
        return redirect('/verify/')

    return render(request, 'pages/register.html')


# ─── Verificación de código (registro y cambio de contraseña) ─────────────


def verify(request):
    email = request.session.get('verify_email')
    verify_mode = request.session.get('verify_mode', 'registration')

    if not email:
        messages.warning(
            request,
            'No hay una verificación pendiente.',
        )
        return redirect('/register/' if verify_mode == 'registration' else '/forgot-password/')

    if request.method == 'POST':
        code_parts = [
            request.POST.get(f'code{i}', '') for i in range(1, 7)
        ]
        code = ''.join(code_parts)

        if not code or len(code) != 6 or not code.isdigit():
            messages.error(request, 'El código debe tener 6 dígitos numéricos.')
            return render(request, 'pages/verification_code.html', {'email': email})

        if verify_mode == 'registration':
            # ── Validar código desde sesión ──────────────────────────
            stored_code = request.session.get('reg_code')
            expires_str = request.session.get('reg_code_expires')

            if not stored_code or not expires_str:
                messages.error(request, 'No hay un código pendiente. Regístrate de nuevo.')
                return redirect('/register/')

            if timezone.now() > timezone.datetime.fromisoformat(expires_str):
                messages.error(request, 'El código ha expirado. Solicita uno nuevo.')
                return render(request, 'pages/verification_code.html', {'email': email})

            if code != stored_code:
                messages.error(request, 'El código ingresado es incorrecto.')
                return render(request, 'pages/verification_code.html', {'email': email})

            # ── Código válido → crear usuario AHORA ─────────────────
            reg_data = request.session.pop('reg_data', {})
            _clean_reg_session(request)

            # Re-verificar uniqueness (por si otro tomó el username, correo o teléfono)
            if Usuario.objects.filter(username=reg_data['username']).exists():
                messages.error(request, 'El nombre de usuario ya fue tomado. Regístrate de nuevo.')
                return redirect('/register/')
            if Usuario.objects.filter(correo=reg_data['correo']).exists():
                messages.error(request, 'El correo ya fue registrado. Regístrate de nuevo.')
                return redirect('/register/')
            if Usuario.objects.filter(telefono=reg_data['telefono']).exists():
                messages.error(request, 'El número de teléfono ya fue registrado. Regístrate de nuevo.')
                return redirect('/register/')

            user = Usuario.objects.create(
                username=reg_data['username'],
                password=make_password(reg_data['password']),
                nombre=reg_data['nombre'],
                apellidos=reg_data.get('apellidos') or None,
                telefono=reg_data['telefono'],
                correo=reg_data['correo'],
                enabled=True,
            )

            request.session['user_id'] = user.id
            request.session['username'] = user.username

            messages.success(request, '¡Registro completado exitosamente!')
            return redirect('/')

        else:
            # ── Modo password_reset: validar contra auth2fa ──────────
            try:
                user = Usuario.objects.get(correo=email)
            except Usuario.DoesNotExist:
                messages.error(request, 'Usuario no encontrado.')
                return redirect('/register/')

            try:
                token_service.validate(
                    user, code, VerificationToken.Type.PASSWORD_CHANGE
                )
            except InvalidToken:
                messages.error(request, 'El código ingresado es incorrecto.')
                return render(request, 'pages/verification_code.html', {'email': email})
            except TokenExpired:
                messages.error(request, 'El código ha expirado. Solicita uno nuevo.')
                return render(request, 'pages/verification_code.html', {'email': email})

            request.session['password_reset_verified'] = True
            request.session['password_reset_email'] = email
            request.session.pop('verify_mode', None)
            messages.success(request, 'Código verificado. Ahora puedes cambiar tu contraseña.')
            return redirect('/reset-password/')

    return render(request, 'pages/verification_code.html', {'email': email})


def _clean_reg_session(request):
    for k in ('reg_code', 'reg_code_expires', 'reg_data', 'verify_email', 'verify_mode'):
        request.session.pop(k, None)


# ─── Reenviar código de verificación ──────────────────────────────────────


def resend_code(request):
    email = request.session.get('verify_email')
    verify_mode = request.session.get('verify_mode', 'registration')

    if not email:
        messages.warning(request, 'No hay verificación pendiente.')
        return redirect('/register/')

    if verify_mode == 'registration':
        reg_data = request.session.get('reg_data')
        if not reg_data:
            messages.error(request, 'Los datos de registro expiraron. Regístrate de nuevo.')
            return redirect('/register/')

        code = _gen_code()
        user_name = f"{reg_data['nombre']} {reg_data.get('apellidos', '')}".strip() or reg_data['username']

        try:
            _send_code_email(email, code, user_name)
        except Exception as e:
            logger.error('Error al reenviar código: %s', e)
            messages.error(request, 'Error al reenviar el código. Intenta de nuevo.')
            return redirect('/verify/')

        request.session['reg_code'] = code
        request.session['reg_code_expires'] = (
            timezone.now() + timedelta(minutes=TOKEN_LIFETIME_MINUTES)
        ).isoformat()
        messages.success(request, f'Se ha reenviado el código a {email}.')
    else:
        try:
            user = Usuario.objects.get(correo=email)
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('/register/')

        try:
            token = token_service.generate(user, VerificationToken.Type.PASSWORD_CHANGE)
            email_sender.send_code(
                to_email=email,
                code=token.code,
                token_type=VerificationToken.Type.PASSWORD_CHANGE,
                user_name=user.get_full_name() or user.username,
            )
            messages.success(request, f'Se ha reenviado el código a {email}.')
        except Exception as e:
            logger.error('Error al reenviar código: %s', e)
            messages.error(request, 'Error al reenviar el código. Intenta de nuevo.')

    return redirect('/verify/')


# ═══════════════════════════════════════════════════════════════════════════
# CAMBIO DE CONTRASEÑA (solo accesible tras verificar código auth2fa)
# ═══════════════════════════════════════════════════════════════════════════


def reset_password(request):
    """Muestra formulario para nueva contraseña (solo si auth2fa verificó)."""
    if not request.session.get('password_reset_verified'):
        messages.warning(request, 'Debes verificar tu identidad primero.')
        return redirect('/forgot-password/')

    email = request.session.get('password_reset_email')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password:
            messages.error(request, 'La nueva contraseña es obligatoria.')
            return render(request, 'pages/reset-password.html')

        if new_password != confirm_password:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'pages/reset-password.html')

        if len(new_password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
            return render(request, 'pages/reset-password.html')

        try:
            user = Usuario.objects.get(correo=email)
            user.password = make_password(new_password)
            user.save(update_fields=['password'])
        except Usuario.DoesNotExist:
            messages.error(request, 'Usuario no encontrado.')
            return redirect('/login/')

        # Limpiar sesión de recuperación
        request.session.pop('password_reset_verified', None)
        request.session.pop('password_reset_email', None)

        messages.success(request, 'Contraseña actualizada exitosamente. Inicia sesión.')
        return redirect('/login/')

    return render(request, 'pages/reset-password.html', {'email': email})


# ─── Recuperar contraseña (paso 1: enviar código) ─────────────────────────


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'El correo es obligatorio.')
            return render(request, 'pages/forgot-password.html')

        # No revelar si el usuario existe (seguridad)
        user_exists = Usuario.objects.filter(correo=email).exists()

        if user_exists:
            user = Usuario.objects.get(correo=email)
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

        # Guardar en sesión para el paso de verificación
        request.session['verify_email'] = email
        request.session['verify_mode'] = 'password_reset'

        messages.success(
            request,
            'Si el correo existe en nuestro sistema, recibirás un código de verificación.',
        )
        return redirect('/verify/')

    return render(request, 'pages/forgot-password.html')


# ═══════════════════════════════════════════════════════════════════════════
# INICIO / CIERRE DE SESIÓN
# ═══════════════════════════════════════════════════════════════════════════


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
                request.session['verify_email'] = user.correo
                request.session['verify_mode'] = 'registration'

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


def logout_view(request):
    request.session.flush()
    messages.info(request, 'Sesión cerrada.')
    return redirect('/login/')
