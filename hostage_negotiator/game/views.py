# game/views.py
import json
import logging
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import User, GameProgress, Score
from .forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm, GameResponseForm
from .game_logic import GameState, process_turn, calculate_game_score
from .grok_client import get_ai_response
from .scenario_manager import ScenarioManager

logger = logging.getLogger(__name__)

def index(request):
    today = datetime.utcnow().date()
    can_play = True
    if request.user.is_authenticated:
        if request.user.last_played_date == today:
            messages.info(request, 'You have already played today. Come back tomorrow!')
            can_play = False
    else:
        last_played = request.session.get('last_played_date')
        if last_played and datetime.strptime(last_played, '%Y-%m-%d').date() == today:
            messages.info(request, 'You have already played today. Come back tomorrow or create an account!')
            can_play = False
            return render(request, 'game/index.html', {'can_play': can_play})
    if not request.user.is_authenticated and can_play:
        return redirect('start_game')
    return render(request, 'game/index.html', {'can_play': can_play})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        # Authenticate using email
        user = User.objects.filter(email=email).first()
        if user and user.check_password(password):
            login(request, user)
            if 'pending_game_state' in request.session:
                game_state = request.session.pop('pending_game_state')
                request.session['game_state'] = game_state
                return redirect('game')
            return redirect('index')
        messages.error(request, 'Invalid email or password')
    return render(request, 'game/login.html', {'form': form})

def register(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if User.objects.filter(username=form.cleaned_data['username']).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(email=form.cleaned_data['email']).exists():
            messages.error(request, 'Email already registered')
        else:
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            messages.success(request, 'Registration successful!')
            return redirect('login')
    return render(request, 'game/register.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

def reset_password_request(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = ResetPasswordRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.filter(email=form.cleaned_data['email']).first()
        if user:
            try:
                token = user.get_reset_password_token()
                # Placeholder for email sending (implement with Django's send_mail or SendGrid)
                messages.info(request, 'Check your email for instructions to reset your password')
            except Exception as e:
                logger.error(f"Error sending reset email: {str(e)}")
                messages.error(request, 'Error sending reset email. Please try again later.')
        else:
            messages.info(request, 'Check your email for instructions to reset your password')
        return redirect('login')
    return render(request, 'game/reset_password_request.html', {'form': form})

def reset_password(request, token):
    if request.user.is_authenticated:
        return redirect('index')
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect('index')
    form = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save()
        messages.success(request, 'Your password has been reset.')
        return redirect('login')
    return render(request, 'game/reset_password.html', {'form': form})

def start_game(request):
    today = datetime.utcnow().date()
    if request.user.is_authenticated and request.user.last_played_date == today:
        messages.error(request, 'You have already played today')
        return redirect('index')
    elif not request.user.is_authenticated:
        last_played = request.session.get('last_played_date')
        if last_played and datetime.strptime(last_played, '%Y-%m-%d').date() == today:
            messages.info(request, 'You have already played today. Create an account for stats tracking!')
            return redirect('index')
    
    daily_scenario = ScenarioManager.get_daily_scenario()
    game_state = GameState(
        tension=5, trust=3, hostages=daily_scenario.hostages, scenario=daily_scenario
    )
    game_state.messages.append(("suspect", daily_scenario.opening_dialogue))
    request.session['game_state'] = game_state.to_dict()
    request.session['last_played_date'] = today.strftime('%Y-%m-%d')  # Track for guests
    return redirect('game')

def game(request):
    if 'game_state' not in request.session:
        return redirect('index')
    game_state = GameState.from_dict(request.session['game_state'])
    form = GameResponseForm()
    return render(request, 'game/game.html', {'game_state': game_state, 'form': form})
def play(request):
    if 'game_state' not in request.session:
        messages.error(request, 'Game session expired. Please start a new game.')
        return redirect('index')
    form = GameResponseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        game_state = GameState.from_dict(request.session['game_state'])
        choice = form.cleaned_data['choice']
        
        if choice.lower() == 'accept surrender' and game_state.surrender_offered:
            game_state.success = True
            game_state.game_over = True
            if request.user.is_authenticated:
                score = save_game_score(request, request.user.id, game_state)
                request.user.last_played_date = datetime.utcnow().date()
                request.user.current_streak += 1
                request.user.highest_streak = max(request.user.current_streak, request.user.highest_streak)
                GameProgress.objects.create(user=request.user, success=True)
                request.user.save()
                return redirect('stats')
            messages.success(request, 'Great job! Create an account to track your progress!')
            return redirect('stats')

        success, message = process_turn(game_state, choice)
        if not success:
            messages.error(request, message)
            return redirect('game')

        ai_response = json.loads(get_ai_response(game_state, choice))
        game_state.tension = ai_response['tension_level']
        game_state.trust = ai_response['trust_level']
        game_state.process_ai_response(ai_response['suspect_response'])

        request.session['game_state'] = game_state.to_dict()
        if game_state.is_game_over():
            if request.user.is_authenticated:
                score = save_game_score(request, request.user.id, game_state)
                request.user.last_played_date = datetime.utcnow().date()
                if game_state.is_success():
                    request.user.current_streak += 1
                    request.user.highest_streak = max(request.user.current_streak, request.user.highest_streak)
                else:
                    request.user.current_streak = 0
                GameProgress.objects.create(user=request.user, success=game_state.is_success())
                request.user.save()
            else:
                messages.info(request, 'Game complete! Create an account to track your progress!')
            return redirect('stats')
        return render(request, 'game/game.html', {'game_state': game_state, 'form': form})
    return redirect('game')

def stats(request):
    user_stats = None
    if request.user.is_authenticated:
        user_stats = {
            'daily_average': request.user.get_daily_average(),
            'lifetime_average': request.user.get_lifetime_average(),
            'current_streak': request.user.current_streak,
            'highest_streak': request.user.highest_streak
        }
    latest_score = request.session.get('latest_score')
    daily_top_scores = Score.get_daily_top_scores()
    all_time_top_scores = Score.get_all_time_top_scores()
    return render(request, 'game/stats.html', {
        'user_stats': user_stats,
        'latest_score': latest_score,
        'daily_top_scores': daily_top_scores,
        'all_time_top_scores': all_time_top_scores,
    })

def save_game_score(request, user_id, game_state):
    score = calculate_game_score(game_state)
    if score and user_id:
        new_score = Score.objects.create(
            user_id=user_id,
            score=score,
            scenario_name=game_state.scenario.name,
            is_daily=True
        )
        # Store latest score in session
        request.session['latest_score'] = {'score': score, 'scenario_name': game_state.scenario.name}
        return new_score
    return None