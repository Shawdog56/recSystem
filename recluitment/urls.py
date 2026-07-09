from django.urls import path
from . import views

urlpatterns = [
    path('', views.hello_world, name='hello_world'),
    path('login/', view=views.login_view, name='pages_login'),
    path('register/', view=views.register, name='pages_registro'),
    path('dashboard/', view=views.dashboard, name='dashboard')
    path('forgot-password/', view=views.forgot_password_view, name='pages_forgot_password'),
    path('verification-code/', view=views.verification_code_view, name='pages_verification_code'),
]