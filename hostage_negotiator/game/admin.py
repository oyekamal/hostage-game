from django.contrib import admin
from .models import User, GameProgress, Score, ScenarioAttempt, GameTurn, PlayerPromise, Scenario

@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ('name', 'suspect', 'suspect_type', 'hostages', 'initial_mood')
    list_filter = ('suspect_type',)
    search_fields = ('name', 'suspect', 'setting')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'setting', 'suspect', 'suspect_type')
        }),
        ('Game Parameters', {
            'fields': ('initial_mood', 'hostages', 'demand', 'goal')
        }),
        ('Dialogue', {
            'fields': ('opening_dialogue',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ScenarioAttempt)
class ScenarioAttemptAdmin(admin.ModelAdmin):
    list_display = ('scenario', 'user', 'start_time', 'success', 'total_turns', 'final_score')
    list_filter = ('scenario', 'success', 'start_time')
    search_fields = ('user__username', 'guest_identifier', 'scenario__name')
    readonly_fields = ('start_time', 'end_time')
    fieldsets = (
        ('Attempt Information', {
            'fields': ('scenario', 'user', 'guest_identifier', 'start_time', 'end_time')
        }),
        ('Game State', {
            'fields': ('initial_tension', 'final_tension', 'initial_trust', 'final_trust', 
                      'initial_hostages', 'final_hostages')
        }),
        ('Results', {
            'fields': ('success', 'surrender_offered', 'total_turns', 'final_score')
        }),
    )

@admin.register(GameTurn)
class GameTurnAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'turn_number', 'tension_change', 'trust_change', 'hostages_released', 'timestamp')
    list_filter = ('attempt__scenario', 'timestamp')
    search_fields = ('attempt__user__username', 'player_input', 'game_response')
    readonly_fields = ('timestamp',)

@admin.register(PlayerPromise)
class PlayerPromiseAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'promise_text', 'turn_made', 'was_kept')
    list_filter = ('was_kept', 'attempt__scenario')
    search_fields = ('promise_text', 'attempt__user__username')

@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'scenario', 'score', 'created_at', 'is_daily')
    list_filter = ('scenario', 'is_daily', 'created_at')
    search_fields = ('user__username', 'guest_identifier', 'scenario__name')
    readonly_fields = ('created_at',)

@admin.register(GameProgress)
class GameProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_scenario', 'total_score', 'highest_scenario_score', 'last_played_at')
    list_filter = ('current_scenario', 'last_played_at')
    search_fields = ('user__username', 'current_scenario__name')
    readonly_fields = ('last_played_at',)
    
    fieldsets = (
        ('Player Information', {
            'fields': ('user', 'current_scenario')
        }),
        ('Progress', {
            'fields': ('completed_scenarios', 'total_score', 'highest_scenario_score')
        }),
        ('Metadata', {
            'fields': ('last_played_at',),
            'classes': ('collapse',)
        }),
    )

# If you're using a custom User model, uncomment and use this instead
# @admin.register(User)
# class CustomUserAdmin(admin.ModelAdmin):
#     list_display = ('username', 'email', 'date_joined', 'last_login', 'is_staff')
#     list_filter = ('is_staff', 'is_superuser', 'is_active')
#     search_fields = ('username', 'email')
#     readonly_fields = ('date_joined', 'last_login')

# If you're using the default Django User model, you can remove this line
admin.site.register(User)
