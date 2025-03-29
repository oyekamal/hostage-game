# game/views.py
import json
import logging
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import User, GameProgress, Score, Scenario, ScenarioAttempt, GameTurn
from .forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm, GameResponseForm
from .game_logic import GameState, process_turn, calculate_game_score
from .grok_client import get_ai_response
from .scenario_manager import ScenarioManager
from django.db.models import Avg

logger = logging.getLogger(__name__)

def index(request):
    current_attempt = None
    can_play = True
    
    today = datetime.utcnow().date().isoformat()
    
    if request.user.is_authenticated:
        # Get any in-progress game from database
        current_attempt = ScenarioAttempt.objects.filter(
            user=request.user,
            end_time__isnull=True
        ).select_related('scenario').first()
        
        # Check if user has played today
        played_today = ScenarioAttempt.objects.filter(
            user=request.user,
            start_time__date=today,
            end_time__isnull=False
        ).exists()
    else:
        # For guests, check session
        guest_last_played = request.session.get('guest_last_played')
        can_play = guest_last_played != today
        current_attempt = request.session.get('guest_current_attempt')
    
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
    today = datetime.utcnow().date().isoformat()
    
    if scenario_id:
        scenario = get_object_or_404(Scenario, id=scenario_id)
    else:
        scenario = Scenario.objects.latest('created_at')
    
    # Check if already played today
    if request.user.is_authenticated:
        existing_attempt = ScenarioAttempt.objects.filter(
            user=request.user,
            scenario=scenario,
            start_time__date=today,
            end_time__isnull=False
        ).exists()
        
        if existing_attempt:
            messages.error(request, 'You have already played today')
            return redirect('index')
    else:
        # Check guest session
        if request.session.get('guest_last_played') == today:
            messages.error(request, 'You have already played today. Come back tomorrow!')
            return redirect('index')
    
    # Create game state
    game_state = GameState(
        tension=5,
        trust=3,
        hostages=scenario.hostages,
        scenario=scenario
    )
    game_state.messages.append(("suspect", scenario.opening_dialogue))
    
    if request.user.is_authenticated:
        # Create database attempt for authenticated users
        attempt = ScenarioAttempt.objects.create(
            user=request.user,
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
        request.session['current_attempt_id'] = attempt.id
    else:
        # Store attempt in session for guests
        guest_attempt = {
            'game_state': game_state.to_dict(),
            'scenario_name': scenario.name,
            'start_time': datetime.utcnow().isoformat()
        }
        request.session['guest_current_attempt'] = guest_attempt
    
    return redirect('game')

def game(request):
    if request.user.is_authenticated:
        attempt_id = request.session.get('current_attempt_id')
        if not attempt_id:
            return redirect('index')
        
        attempt = get_object_or_404(ScenarioAttempt, id=attempt_id)
        game_state = attempt.get_game_state()
    else:
        guest_attempt = request.session.get('guest_current_attempt')
        if not guest_attempt:
            return redirect('index')
        
        game_state = GameState.from_dict(guest_attempt['game_state'])
    
    form = GameResponseForm()
    
    context = {
        'game_state': game_state,
        'form': form,
        'hostages_remaining': game_state.hostages - game_state.hostages_released,
        'hostages_released': game_state.hostages_released
    }
    
    return render(request, 'game/game.html', context)

def play(request):
    if request.user.is_authenticated:
        attempt_id = request.session.get('current_attempt_id')
        if not attempt_id:
            messages.error(request, 'No active game found.')
            return redirect('index')
            
        attempt = get_object_or_404(ScenarioAttempt, id=attempt_id)
        game_state = attempt.get_game_state()
    else:
        guest_attempt = request.session.get('guest_current_attempt')
        if not guest_attempt:
            messages.error(request, 'No active game found.')
            return redirect('index')
            
        game_state = GameState.from_dict(guest_attempt['game_state'])
    
    # Check if game should be ended
    if game_state.turn >= 10 or game_state.game_over:
        game_state.game_over = True
        if game_state.tension <= 2 and game_state.trust >= 7:
            game_state.success = True
            game_state.messages.append(("system", "The suspect's resolve has completely broken. Negotiation successful!"))
        else:
            game_state.success = False
            game_state.messages.append(("system", "Time has run out. Negotiation failed."))
        
        if request.user.is_authenticated:
            attempt.update_from_game_state(game_state)
            attempt.end_time = datetime.utcnow()
            attempt.save()
            save_game_score(request, request.user.id, game_state)
            request.session.pop('current_attempt_id', None)
            return redirect('stats')
        else:
            # For guests, mark the day as played and clear current attempt
            request.session['guest_last_played'] = datetime.utcnow().date().isoformat()
            request.session.pop('guest_current_attempt', None)
            return redirect('index')
    
    form = GameResponseForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        choice = form.cleaned_data['choice']
        
        if not game_state.messages or game_state.messages[-1] != ("player", choice):
            # Add player's message
            game_state.messages.append(("player", choice))
            
            # Get AI response
            ai_response_data = get_ai_response(game_state, choice)
            
            try:
                ai_response = json.loads(ai_response_data)
                
                # Update game state based on AI response
                game_state.tension = ai_response.get('tension_level', game_state.tension)
                game_state.trust = ai_response.get('trust_level', game_state.trust)
                
                # Update turn counter
                game_state.turn += 1
                
                # Save the updated state
                if request.user.is_authenticated:
                    attempt.update_from_game_state(game_state)
                    attempt.save()
                else:
                    guest_attempt['game_state'] = game_state.to_dict()
                    request.session['guest_current_attempt'] = guest_attempt
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to parse AI response: {ai_response_data}")
                messages.error(request, "An error occurred while processing your response.")
    
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
