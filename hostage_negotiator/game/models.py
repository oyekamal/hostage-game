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

class GameProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='game_progress')
    played_date = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=['user', 'played_date'])]

class Score(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='scores')
    guest_identifier = models.CharField(max_length=64, null=True, blank=True)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    scenario_name = models.CharField(max_length=128)
    is_daily = models.BooleanField(default=True)

    @staticmethod
    def get_daily_top_scores(limit=10):
        today = datetime.utcnow().date()
        return Score.objects.filter(created_at__date=today).order_by('-score')[:limit]

    @staticmethod
    def get_all_time_top_scores(limit=10):
        return Score.objects.filter(is_daily=False).order_by('-score')[:limit]

    @staticmethod
    def update_all_time_leaderboard():
        today = datetime.utcnow().date()
        daily_top_scores = Score.objects.filter(created_at__date=today).order_by('-score')[:10]
        for score in daily_top_scores:
            Score.objects.create(
                user=score.user,
                guest_identifier=score.guest_identifier,
                score=score.score,
                scenario_name=score.scenario_name,
                is_daily=False,
                created_at=score.created_at
            )