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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='scenario_attempts')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='attempts')
    guest_identifier = models.CharField(max_length=64, null=True, blank=True)
    scenario_name = models.CharField(max_length=128)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    initial_tension = models.IntegerField()
    initial_trust = models.IntegerField()
    final_tension = models.IntegerField(null=True)
    final_trust = models.IntegerField(null=True)
    initial_hostages = models.IntegerField()
    final_hostages = models.IntegerField(null=True)
    success = models.BooleanField(default=False)
    surrender_offered = models.BooleanField(default=False)
    total_turns = models.IntegerField(default=0)
    final_score = models.FloatField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['scenario_name']),
            models.Index(fields=['scenario']),
        ]

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

class GameProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    current_scenario = models.ForeignKey(Scenario, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_players')
    completed_scenarios = models.ManyToManyField(Scenario, related_name='completed_by', blank=True)
    total_score = models.IntegerField(default=0)
    highest_scenario_score = models.IntegerField(default=0)
    last_played_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Game Progress"
        indexes = [
            models.Index(fields=['user', 'last_played_at']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Progress"
