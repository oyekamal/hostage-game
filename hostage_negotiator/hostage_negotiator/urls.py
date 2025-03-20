"""
URL configuration for hostage_negotiator project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# hostage_negotiator/urls.py
from django.contrib import admin
from django.urls import path
from game import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),  # Root URL maps to index view
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('reset_password_request/', views.reset_password_request, name='reset_password_request'),
    path('reset_password/<str:token>/', views.reset_password, name='reset_password'),
    path('start_game/', views.start_game, name='start_game'),
    path('game/', views.game, name='game'),
    path('play/', views.play, name='play'),
    path('stats/', views.stats, name='stats'),
]