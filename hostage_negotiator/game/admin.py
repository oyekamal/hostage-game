from django.contrib import admin
from .models import User, GameProgress, Score

admin.site.register(User)
admin.site.register(GameProgress)
admin.site.register(Score)