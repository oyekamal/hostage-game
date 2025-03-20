import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("api_key")
import logging
import random
import json
from openai import OpenAI
from functools import lru_cache
import hashlib
import time

# Initialize Grok AI client
client = OpenAI(
    base_url="https://api.x.ai/v1",
    api_key=api_key
)

@lru_cache(maxsize=1000)
def get_cached_response(input_hash, mood, suspect_type):
    """Cache for AI responses based on input and context"""
    return None  # Return None to indicate cache miss

def get_ai_response(game_state, player_choice):
    """Generate an emotionally intelligent response based on game state and player choice."""
    try:
        # Generate cache key based on input and context
        cache_key = hashlib.md5(
            f"{player_choice}:{game_state.tension}:{game_state.scenario.suspect_type}".encode()
        ).hexdigest()

        # Check cache first
        cached_response = get_cached_response(cache_key, game_state.tension, game_state.scenario.suspect_type)
        if cached_response:
            return cached_response

        # Create dynamic system message
        system_message = f"""You are a highly realistic hostage-taker AI, trained on real-world crisis psychology and FBI tactics. Keep responses concise, impactful, and focused on demands.

        🧠 Core Rules:
        - Keep responses under 30 words
        - Focus on immediate demands and consequences
        - No solutions or hints
        - Stay in character
        - React with emotional complexity
        - Ensure 5-10 turn gameplay

        Current Profile:
        - Tension: {game_state.tension}/10
        - Hostages: {game_state.hostages - game_state.hostages_released}
        - Demand: {game_state.scenario.demand}
        - Trust: {game_state.trust}/10"""

        # Build prompt with current context
        prompt = f"""Current Situation:
Turn: {game_state.turn}/10
Tension: {game_state.tension}/10
Trust: {game_state.trust}/10

Negotiator Says: "{player_choice}"

Generate a short, tense response that:
1. Matches tension level ({game_state.tension}/10)
2. Shows authentic crisis behavior
3. Keeps focus on demands
4. Maintains intensity without being verbose"""

        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content.strip()

        # Clean up response formatting
        ai_response = ai_response.strip('"\'')  # Remove quotes
        ai_response = ai_response.split('\n')[0]  # Take only the first line
        ai_response = ai_response.split('{')[0].strip()  # Remove any JSON-like content

        # Track repetition silently
        input_history = [msg[1] for msg in game_state.messages[-5:] if msg[0] == 'player']
        if input_history.count(player_choice) > 3:
            game_state.tension += 1
            game_state.trust -= 1

        # Cache the successful response
        get_cached_response.cache_info()
        get_cached_response(cache_key, game_state.tension, game_state.scenario.suspect_type)

        # Return structured JSON with cleaned response
        ai_response_dict = {
            "suspect_response": ai_response,
            "tension_level": game_state.tension,
            "trust_level": game_state.trust,
            "hostage_count": game_state.hostages - game_state.hostages_released,
            "turn_count": game_state.turn,
            "recommended_ui_action": "Show suspect with tension-appropriate behavior",
            "daily_hint": random.choice([
                "Tomorrow will test you further!",
                "A bigger crisis awaits tomorrow!",
                "Prepare for more tomorrow!"
            ])
        }
        return json.dumps(ai_response_dict)

    except Exception as e:
        logging.error(f"Error getting AI response: {e}")
        return json.dumps(get_fallback_response(game_state.tension))

def get_fallback_response(tension):
    """Get fallback response based on tension level"""
    fallback_responses = {
        range(0, 2): "Maybe you're right... I just want this to end without anyone getting hurt.",
        range(2, 4): "I'm listening... but I still don't fully trust this.",
        range(4, 7): "You better not be playing games with me! I MEAN IT!",
        range(7, 11): "SHUT UP! ONE MORE WORD AND SOMEONE DIES RIGHT NOW!"
    }
    current_tension_range = next(
        tension_range for tension_range in fallback_responses.keys() 
        if tension in tension_range
    )
    return {
        "suspect_response": fallback_responses[current_tension_range],
        "tension_level": tension,
        "trust_level": 0,
        "hostage_count": 0,
        "turn_count": 0,
        "recommended_ui_action": "Show suspect with tension-appropriate behavior",
        "daily_hint": "Try again tomorrow!"
    }

def analyze_game_session(game_state):
    """Generate a detailed analysis of the negotiation session."""
    try:
        system_message = """You are an expert trainer analyzing a premium user's negotiation session. Provide a concise analysis (max 200 words) with: Key Moments, Response Effectiveness, Trust Insights, Improvement Tips, 1-5 Star Rating."""

        game_history = "\n".join([
            f"Turn {i+1}: {msg[1][:100]}..." if len(msg[1]) > 100 else f"Turn {i+1}: {msg[1]}"
            for i, msg in enumerate(game_state.messages) if msg[0] == 'player'
        ])

        prompt = f"""Analyze this negotiation session:
Scenario: {game_state.scenario.name}
Type: {game_state.scenario.suspect_type}
Initial/Final Tension: {game_state.scenario.initial_mood}/{game_state.tension}
Success: {game_state.success}

History:
{game_history}"""

        response = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,
            timeout=15
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"Error generating game analysis: {e}")
        return "Unable to generate analysis at this time. Please try again later."
