from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import datetime
import jwt
from django.conf import settings
import time

class User(AbstractUser):
    email = models.EmailField(unique=True)
    last_played_date = models.DateField(null=True, blank=True)
    current_streak = models.IntegerField(default=0)
    highest_streak = models.IntegerField(default=0)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time.time() + expires_in},
            settings.SECRET_KEY, algorithm='HS256'
        ).decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])['reset_password']
            return User.objects.get(id=id)
        except:
            return None

    def get_daily_average(self):
        today = datetime.utcnow().date()
        daily_scores = Score.objects.filter(user=self, created_at__date=today)
        if not daily_scores:
            return None
        return sum(s.score for s in daily_scores) / len(daily_scores)

    def get_lifetime_average(self):
        scores = Score.objects.filter(user=self)
        if not scores:
            return None
        return sum(s.score for s in scores) / len(scores)

class Scenario(models.Model):
    name = models.CharField(max_length=255)
    setting = models.CharField(max_length=255)
    suspect = models.CharField(max_length=255)
    initial_mood = models.IntegerField()
    hostages = models.IntegerField()
    opening_dialogue = models.TextField()
    demand = models.CharField(max_length=255)
    goal = models.CharField(max_length=255)
    suspect_type = models.CharField(max_length=20, default='pragmatic')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Scenario'
        verbose_name_plural = 'Scenarios'

    def __str__(self):
        return self.name

class ScenarioAttempt(models.Model):
    EMOTIONAL_STATES = [
        ('volatile', 'Volatile (Mood 7+)'),
        ('agitated', 'Agitated (Mood 4-6)'),
        ('strategic', 'Strategic (Mood 2-3)'),
        ('resigned', 'Resigned (Mood 0-1)')
    ]

    # Existing fields
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE)
    scenario_name = models.CharField(max_length=255)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Updated tracking fields
    initial_tension = models.IntegerField()
    current_tension = models.IntegerField()
    final_tension = models.IntegerField(null=True)
    
    initial_trust = models.IntegerField()
    current_trust = models.IntegerField()
    final_trust = models.IntegerField(null=True)
    
    initial_hostages = models.IntegerField()
    current_hostages = models.IntegerField()
    final_hostages = models.IntegerField(null=True)
    
    # New psychological tracking
    emotional_state = models.CharField(max_length=20, choices=EMOTIONAL_STATES, default='agitated')
    mirroring_count = models.IntegerField(default=0)
    emotional_labeling_success = models.IntegerField(default=0)
    emotional_labeling_failure = models.IntegerField(default=0)
    tactical_empathy_success = models.IntegerField(default=0)
    tactical_empathy_failure = models.IntegerField(default=0)
    
    # Game progress
    current_turn = models.IntegerField(default=1)
    total_turns = models.IntegerField(default=0)
    game_over = models.BooleanField(default=False)
    success = models.BooleanField(null=True)
    final_score = models.IntegerField(null=True)
    
    # Negotiation tracking
    messages = models.JSONField(default=list)
    good_choice_streak = models.IntegerField(default=0)
    promises_kept = models.JSONField(default=list)
    rapport = models.IntegerField(default=0)
    hostages_released = models.IntegerField(default=0)
    surrender_offered = models.BooleanField(default=False)
    poor_choices = models.IntegerField(default=0)
    similar_inputs_count = models.IntegerField(default=0)
    last_input_type = models.CharField(max_length=50, null=True)
    emotional_appeals_count = models.IntegerField(default=0)

    def update_emotional_state(self):
        if self.current_tension >= 7:
            self.emotional_state = 'volatile'
        elif 4 <= self.current_tension <= 6:
            self.emotional_state = 'agitated'
        elif 2 <= self.current_tension <= 3:
            self.emotional_state = 'strategic'
        else:
            self.emotional_state = 'resigned'

    def get_game_state(self):
        """Convert attempt data to GameState object"""
        from .game_logic import GameState
        
        game_state = GameState(
            turn=self.current_turn,
            tension=self.current_tension,
            trust=self.current_trust,
            hostages=self.current_hostages,
            messages=self.messages,
            game_over=self.game_over,
            success=self.success,
            scenario=self.scenario,
            good_choice_streak=self.good_choice_streak,
            promises_kept=self.promises_kept,
            rapport=self.rapport,
            hostages_released=self.hostages_released,
            surrender_offered=self.surrender_offered,
            poor_choices=self.poor_choices,
            similar_inputs_count=self.similar_inputs_count,
            last_input_type=self.last_input_type,
            emotional_appeals_count=self.emotional_appeals_count
        )
        return game_state

    def update_from_game_state(self, game_state):
        """Update attempt with current game state"""
        self.current_tension = game_state.tension
        self.current_trust = game_state.trust
        self.current_hostages = game_state.hostages
        self.messages = game_state.messages
        self.hostages_released = game_state.hostages_released
        self.current_turn = game_state.turn  # Make sure this line exists
        self.total_turns = game_state.turn
        self.game_over = game_state.game_over
        self.success = game_state.success
        self.good_choice_streak = game_state.good_choice_streak
        self.promises_kept = game_state.promises_kept
        self.rapport = game_state.rapport
        self.poor_choices = game_state.poor_choices
        self.similar_inputs_count = game_state.similar_inputs_count
        self.last_input_type = game_state.last_input_type
        self.emotional_appeals_count = game_state.emotional_appeals_count
        
        self.update_emotional_state()
        
        if game_state.game_over:
            self.end_time = datetime.utcnow()
            self.final_tension = game_state.tension
            self.final_trust = game_state.trust
            self.final_hostages = game_state.hostages
        
        self.save()

    def __str__(self):
        return f"Attempt #{self.id} - {self.scenario_name} by {self.user.username if self.user else 'Guest'}"

class Score(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='scores')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='scores')
    guest_identifier = models.CharField(max_length=64, null=True, blank=True)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_name = models.CharField(max_length=128)
    is_daily = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['scenario']),
            models.Index(fields=['created_at']),
        ]

    @classmethod
    def get_daily_top_scores(cls, limit=10):
        today = datetime.utcnow().date()
        return cls.objects.filter(
            created_at__date=today,
            is_daily=True
        ).select_related('user', 'scenario').order_by('-score')[:limit]

    @classmethod
    def get_all_time_top_scores(cls, limit=10):
        return cls.objects.filter(
            is_daily=False
        ).select_related('user', 'scenario').order_by('-score')[:limit]

    @classmethod
    def update_all_time_leaderboard(cls):
        today = datetime.utcnow().date()
        daily_top_scores = cls.objects.filter(
            created_at__date=today,
            is_daily=True
        ).order_by('-score')[:10]
        
        for score in daily_top_scores:
            cls.objects.create(
                user=score.user,
                scenario=score.scenario,
                guest_identifier=score.guest_identifier,
                score=score.score,
                scenario_name=score.scenario_name,
                is_daily=False,
                created_at=score.created_at
            )

    def __str__(self):
        return f"Score: {self.score} - {self.scenario_name} by {self.user.username if self.user else 'Guest'}"

class GameTurn(models.Model):
    attempt = models.ForeignKey(ScenarioAttempt, on_delete=models.CASCADE, related_name='turns')
    turn_number = models.IntegerField()
    player_input = models.TextField()
    game_response = models.TextField()
    tension_change = models.IntegerField()
    trust_change = models.IntegerField()
    hostages_released = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['attempt', 'turn_number']),
        ]
        ordering = ['turn_number']

    def __str__(self):
        return f"Turn {self.turn_number} of Attempt #{self.attempt_id}"

class PlayerPromise(models.Model):
    attempt = models.ForeignKey(ScenarioAttempt, on_delete=models.CASCADE, related_name='promises')
    promise_text = models.TextField()
    turn_made = models.IntegerField()
    was_kept = models.BooleanField(default=False)
    turn_resolved = models.IntegerField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['attempt']),
        ]

    def __str__(self):
        status = "Kept" if self.was_kept else "Pending" if self.turn_resolved is None else "Broken"
        return f"Promise: {self.promise_text[:30]}... ({status})"

class GameProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    current_scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_players')
    completed_scenarios = models.ManyToManyField(Scenario, related_name='completed_by', blank=True)
    total_score = models.IntegerField(default=0)
    highest_scenario_score = models.IntegerField(default=0)
    last_played_at = models.DateTimeField(auto_now=True)
    success_count = models.IntegerField(default=0)  # Add this field to track successful games
    total_games = models.IntegerField(default=0)    # Add this field to track total games

    class Meta:
        verbose_name_plural = "Game Progress"
        indexes = [
            models.Index(fields=['user', 'last_played_at']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Progress"
