from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('scenarios/', views.scenario_list, name='scenario_list'),
    path('start/<int:scenario_id>/', views.start_game, name='start_game'),
    path('start/', views.start_game, name='start_daily_game'),
    path('game/', views.game, name='game'),
    path('play/', views.play, name='play'),
    path('history/', views.game_history, name='game_history'),
    path('resume/<int:attempt_id>/', views.resume_game, name='resume_game'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('stats/', views.stats, name='stats'),
    path('reset_password_request/', views.reset_password_request, name='reset_password_request'),
    path('reset_password/<str:token>/', views.reset_password, name='reset_password'),
]
