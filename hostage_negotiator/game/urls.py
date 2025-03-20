from django.contrib import admin
from django.urls import path
from game import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('reset_password_request/', views.reset_password_request, name='reset_password_request'),
    path('reset_password/<token>/', views.reset_password, name='reset_password'),
    path('start_game/', views.start_game, name='start_game'),
    path('game/', views.game, name='game'),
    path('play/', views.play, name='play'),
    path('stats/', views.stats, name='stats'),
]