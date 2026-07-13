from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password,  make_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Usuario

# Create your views here.
def hello_world(request):
    return render(request, 'index.html')

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')


@login_required(login_url='pages_login')
def vacancy_creation_view(request):
    if request.method == 'POST':
        messages.success(request, 'Vacante recibida correctamente.')
        return redirect('pages_vacancy_creation')

    return render(request, 'pages/vacancy-creation.html')


def register(request):
    if request.method == 'POST':
        # Retrieve data from form
        username = request.POST.get('username')
        password = request.POST.get('password')
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        correo = request.POST.get('correo')
        
        new_user = Usuario(
            username=username,
            password=make_password(password),
            nombre=nombre,
            telefono=telefono,
            correo=correo
        )
        new_user.save()
        return redirect('pages_login') # Redirect to login page after registration
        
    return render(request, 'pages/register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = Usuario.objects.get(username=username)
            
            if check_password(password, user.password):
                roles = list(user.roles.values_list('descripcion',flat=True))
                print(roles)
                request.session['roles'] = roles
                request.session['user_id'] = user.id
                login(request, user)
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, "Invalid credentials")
        except Usuario.DoesNotExist as e:
            messages.error(request, "User does not exist")
            
    return render(request, 'pages/login.html')


def forgot_password_view(request):
    return render(request, 'pages/forgot-password.html')


def verification_code_view(request):
    return render(request, 'pages/verification_code.html')