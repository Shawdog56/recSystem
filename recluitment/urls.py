from django.urls import path
from . import views

urlpatterns = [
    path('', views.hello_world, name='hello_world'),
    path('login/', view=views.login_view, name='pages_login'),
    path('register/', view=views.register, name='pages_registro'),
    path('dashboard/', view=views.dashboard, name='dashboard')
]