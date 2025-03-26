# game/views.py
import json
import logging
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import User, GameProgress, Score, Scenario, ScenarioAttempt
from .forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm, GameResponseForm
from .game_logic import GameState, process_turn, calculate_game_score
from .grok_client import get_ai_response
from .scenario_manager import ScenarioManager
from django.db.models import Avg

logger = logging.getLogger(__name__)

def index(request):
    current_attempt = None
    can_play = True
    
    if request.user.is_authenticated:
        # Get any in-progress game
        current_attempt = ScenarioAttempt.objects.filter(
            user=request.user,
            end_time__isnull=True
        ).select_related('scenario').first()
        
        # Check if user has played today
        today = datetime.utcnow().date()
        played_today = ScenarioAttempt.objects.filter(
            user=request.user,
            start_time__date=today,
            end_time__isnull=False
        ).exists()
        
        can_play = not played_today
    
    return render(request, 'game/index.html', {
        'current_attempt': current_attempt,
        'can_play': can_play
    })

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

@login_required
def scenario_list(request):
    scenarios = Scenario.objects.all()
    completed_attempts = ScenarioAttempt.objects.filter(
        user=request.user,
        end_time__isnull=False
    ).select_related('scenario')
    
    # Get user's current progress
    progress, _ = GameProgress.objects.get_or_create(user=request.user)
    
    scenario_data = []
    for scenario in scenarios:
        scenario_attempts = completed_attempts.filter(scenario=scenario)
        best_score = scenario_attempts.order_by('-final_score').first()
        
        scenario_data.append({
            'scenario': scenario,
            'attempts_count': scenario_attempts.count(),
            'best_score': best_score.final_score if best_score else None,
            'completed': scenario in progress.completed_scenarios.all()
        })
    
    return render(request, 'game/scenario_list.html', {
        'scenario_data': scenario_data
    })

def start_game(request, scenario_id=None):
    if scenario_id:
        scenario = get_object_or_404(Scenario, id=scenario_id)
    else:
        scenario = Scenario.objects.latest('created_at')
    
    # Check if user already played this scenario today
    today = datetime.utcnow().date()
    if request.user.is_authenticated:
        existing_attempt = ScenarioAttempt.objects.filter(
            user=request.user,
            scenario=scenario,
            start_time__date=today,
            end_time__isnull=False
        ).exists()
        
        if existing_attempt:
            messages.error(request, 'You have already played this scenario today')
            return redirect('scenario_list')
    
    # Create game state
    game_state = GameState(
        tension=5,
        trust=3,
        hostages=scenario.hostages,
        scenario=scenario
    )
    game_state.messages.append(("suspect", scenario.opening_dialogue))
    
    # Create scenario attempt
    attempt = ScenarioAttempt.objects.create(
        user=request.user if request.user.is_authenticated else None,
        scenario=scenario,
        scenario_name=scenario.name,
        initial_tension=game_state.tension,
        initial_trust=game_state.trust,
        initial_hostages=game_state.hostages,
        current_tension=game_state.tension,
        current_trust=game_state.trust,
        current_hostages=game_state.hostages,
        messages=game_state.messages
    )
    
    # Store attempt ID in session
    request.session['current_attempt_id'] = attempt.id
    
    return redirect('game')

def game(request):
    attempt_id = request.session.get('current_attempt_id')
    if not attempt_id:
        return redirect('index')
    
    attempt = get_object_or_404(ScenarioAttempt, id=attempt_id)
    game_state = attempt.get_game_state()
    form = GameResponseForm()
    
    return render(request, 'game/game.html', {
        'game_state': game_state,
        'form': form,
        'attempt': attempt
    })

@login_required
def play(request):
    attempt_id = request.session.get('current_attempt_id')
    if not attempt_id:
        messages.error(request, 'No active game found.')
        return redirect('index')
        
    attempt = get_object_or_404(ScenarioAttempt, id=attempt_id)
    game_state = attempt.get_game_state()
    
    form = GameResponseForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        choice = form.cleaned_data['choice']
        
        success, message = process_turn(game_state, choice)
        if not success:
            messages.error(request, message)
            return redirect('game')

        ai_response = json.loads(get_ai_response(game_state, choice))
        game_state.tension = ai_response['tension_level']
        game_state.trust = ai_response['trust_level']
        
        # Check for game-ending conditions
        if game_state.tension >= 10:
            game_state.game_over = True
            game_state.success = False
            game_state.hostages -= 1
            game_state.messages.append(("system", "The situation has escalated beyond control. A hostage has been harmed."))
            
            # Update attempt with final state
            attempt.end_time = datetime.utcnow()
            attempt.success = False
            attempt.final_score = calculate_game_score(game_state)
            attempt.update_from_game_state(game_state)
            attempt.save()
            
            messages.error(request, "Game Over - The situation escalated beyond control.")
            return redirect('stats')  # or wherever you want to redirect after game over
        
        # Update attempt with current game state
        attempt.update_from_game_state(game_state)
        attempt.save()
        
        return redirect('game')
    
    return redirect('game')

def stats(request):
    user_stats = None
    if request.user.is_authenticated:
        attempts = ScenarioAttempt.objects.filter(user=request.user)
        user_stats = {
            'total_attempts': attempts.count(),
            'successful_attempts': attempts.filter(success=True).count(),
            'average_score': attempts.filter(final_score__isnull=False).aggregate(Avg('final_score'))['final_score__avg'],
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
        attempt = ScenarioAttempt.objects.get(id=request.session.get('current_attempt_id'))
        new_score = Score.objects.create(
            user_id=user_id,
            score=score,
            scenario=game_state.scenario,  # Add the scenario
            scenario_name=game_state.scenario.name,
            is_daily=True
        )
        # Store latest score in session
        request.session['latest_score'] = {'score': score, 'scenario_name': game_state.scenario.name}
        return new_score
    return None

@login_required
def game_history(request):
    attempts = ScenarioAttempt.objects.filter(
        user=request.user
    ).select_related('scenario').order_by('-start_time')
    
    return render(request, 'game/history.html', {
        'attempts': attempts
    })

@login_required
def resume_game(request, attempt_id):
    attempt = get_object_or_404(ScenarioAttempt, id=attempt_id, user=request.user, end_time__isnull=True)
    request.session['current_attempt_id'] = attempt.id
    return redirect('game')
