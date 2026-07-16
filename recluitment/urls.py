from django.urls import path
from . import views

urlpatterns = [
    path('', views.hello_world, name='hello_world'),
    path('login/', view=views.login_view, name='pages_login'),
    path('register/', view=views.register, name='pages_registro'),
    path('dashboard/', view=views.dashboard, name='dashboard'),
    path('verify/', views.verify, name='verify'),
    path('verification-code/', views.verify, name='pages_verification_code'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('forgot-password/', view=views.forgot_password, name='pages_forgot_password'),
    path('reset-password/', view=views.reset_password, name='reset_password'),
    path('logout/', views.logout_view, name='logout'),
    path('vacantes/crear/', view=views.vacancy_creation_view, name='pages_vacancy_creation'),
]