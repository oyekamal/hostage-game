import os
from dotenv import load_dotenv
import json
import random
import requests
import logging
from functools import lru_cache
import hashlib

# Load .env file
load_dotenv()

# Use uppercase for environment variables by convention
API_KEY = os.getenv("API_KEY")

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1000)
def get_cached_response(input_hash, tension, suspect_type):
    """Cache for AI responses based on input and context"""
    return None

def get_ai_response(game_state, choice, offer=None, green_beret_action=None):
    """Generate an AI response based on game state and player choice."""
    try:
        # Generate cache key
        cache_key = hashlib.md5(
            f"{choice}:{game_state.tension}:{game_state.scenario.suspect_type}".encode()
        ).hexdigest()

        # Check cache first
        cached_response = get_cached_response(cache_key, game_state.tension, game_state.scenario.suspect_type)
        if cached_response:
            return cached_response

        if not API_KEY:
            return json.dumps(get_mock_response(game_state))

        tension_level = game_state.tension
        trust_level = game_state.trust
        scenario = game_state.scenario

        # Determine emotional state
        emotional_state = get_emotional_state(tension_level)

        # Handle special scenarios
        if green_beret_action:
            return handle_green_beret_scenario(game_state, green_beret_action)

        # Build system message
        system_message = build_system_message(game_state, emotional_state)

        # Build user prompt
        user_prompt = build_user_prompt(game_state, choice, offer, emotional_state)

        # Make API call
        response = make_api_call(system_message, user_prompt)
        
        # Process response
        processed_response = process_api_response(response, game_state)
        
        # Cache the response
        get_cached_response(cache_key, tension_level, game_state.scenario.suspect_type)
        
        return json.dumps(processed_response)

    except Exception as e:
        logger.error(f"Error in get_ai_response: {e}")
        return json.dumps(get_fallback_response(game_state.tension))

def get_emotional_state(tension):
    """Determine emotional state based on tension level"""
    if tension >= 7:
        return 'volatile'
    elif tension >= 4:
        return 'agitated'
    elif tension >= 2:
        return 'strategic'
    else:
        return 'resigned'

def handle_green_beret_scenario(game_state, action_type):
    """Handle special Green Beret scenarios"""
    if action_type == "green_beret_scenario":
        return handle_automatic_win(game_state)
    elif action_type == "tactical_intervention":
        return handle_tactical_intervention(game_state)

def build_system_message(game_state, emotional_state):
    """Build the system message for the AI"""
    return f"""You are a highly realistic hostage-taker AI in a {emotional_state} state.
Current Profile:
- Tension: {game_state.tension}/10
- Trust: {game_state.trust}/10
- Hostages: {game_state.hostages - game_state.hostages_released}
- Demand: {game_state.scenario.demand}

Emotional State Rules:
{get_emotional_state_rules(emotional_state)}"""

def build_user_prompt(game_state, choice, offer, emotional_state):
    """Build the user prompt for the AI"""
    return f"""Current Situation:
Turn: {game_state.turn}/10
Tension: {game_state.tension}/10
Trust: {game_state.trust}/10
Emotional State: {emotional_state}

Negotiator Says: "{choice}"
{f'Offer: {offer}' if offer else ''}

Generate a response that:
1. Matches tension level ({game_state.tension}/10)
2. Shows authentic crisis behavior
3. Maintains scenario consistency
4. Keeps focus on demands"""

def make_api_call(system_message, user_prompt):
    """Make the API call to the AI service"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-2",  # Updated model name
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    logger.debug("Making API call to Grok")
    logger.debug(f"Payload: {payload}")
    
    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        json=payload,
        headers=headers,
        timeout=15
    )
    
    logger.debug(f"API response status: {response.status_code}")
    logger.debug(f"API response content: {response.text}")
    
    if response.status_code != 200:
        logger.error(f"API error: {response.text}")
        return {"choices": [{"message": {"content": get_fallback_response(0)["suspect_response"]}}]}
        
    return response.json()

def get_mock_response(game_state):
    """Generate more realistic mock responses based on game state"""
    emotional_state = game_state.get_emotional_state()
    
    responses = {
        'volatile': [
            "Don't try anything stupid! I'm watching every move!",
            "You better take me seriously or someone gets hurt!",
            "Time is running out! Make it happen NOW!"
        ],
        'agitated': [
            "I need guarantees before we move forward.",
            "Your words mean nothing without action!",
            "Show me you're serious about meeting my demands."
        ],
        'strategic': [
            "Let's be clear about what each side needs here.",
            "I'm listening, but I need more than just promises.",
            "We can work this out if you meet my terms."
        ],
        'resigned': [
            "Maybe we can find a way out of this...",
            "I never wanted anyone to get hurt...",
            "What assurances can you give me?"
        ]
    }
    
    suspect_response = random.choice(responses.get(emotional_state, responses['strategic']))
    
    return {
        "tension_level": max(1, min(10, game_state.tension)),
        "trust_level": max(1, min(10, game_state.trust)),
        "suspect_response": suspect_response,
        "counter_offer": None,
        "daily_hint": get_contextual_hint(game_state),
        "hostage_count": game_state.hostages,
        "turn_count": game_state.turn
    }

def get_contextual_hint(game_state):
    """Generate contextual hints based on game state"""
    if game_state.tension >= 8:
        return "Tension is very high. Focus on de-escalation."
    elif game_state.trust <= 3:
        return "Trust is low. Show empathy and understanding."
    elif game_state.turn >= 8:
        return "Time is running out. Consider making a significant offer."
    else:
        return "Keep building rapport through active listening."

def get_fallback_response(tension):
    """Get fallback response based on tension level"""
    fallback_responses = {
        range(0, 3): "I hear you... let's keep talking.",
        range(3, 6): "You better make this worth my time!",
        range(6, 8): "Don't try anything stupid!",
        range(8, 11): "One wrong move and this ends badly!"
    }
    current_range = next(r for r in fallback_responses.keys() if tension in r)
    return {
        "tension_level": tension,
        "trust_level": 0,
        "suspect_response": fallback_responses[current_range],
        "counter_offer": None,
        "daily_hint": "System recovering, try again.",
        "hostage_count": 0,
        "turn_count": 0
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

def get_emotional_state_rules(emotional_state):
    """Get rules for different emotional states"""
    rules = {
        'volatile': "Highly unstable, prone to violent outbursts, requires extreme caution",
        'agitated': "Easily provoked, needs reassurance, sensitive to threats",
        'strategic': "Calculated responses, focused on demands, evaluates options",
        'resigned': "More open to negotiation, showing signs of fatigue or doubt"
    }
    return rules.get(emotional_state, rules['strategic'])

def process_api_response(response, game_state):
    """Process the API response and format it for the game"""
    try:
        if 'choices' not in response or not response['choices']:
            return get_fallback_response(game_state.tension)

        ai_message = response['choices'][0]['message']['content']
        
        # Calculate remaining hostages
        remaining_hostages = game_state.hostages - game_state.hostages_released
        
        # Add the AI response to messages
        game_state.messages.append(("suspect", ai_message))
        
        return {
            "tension_level": game_state.tension,
            "trust_level": game_state.trust,
            "suspect_response": ai_message,
            "counter_offer": None,
            "daily_hint": get_contextual_hint(game_state),
            "hostage_count": remaining_hostages,
            "turn_count": game_state.turn,
            "hostages_released": game_state.hostages_released,
            "messages": game_state.messages  # Include updated messages
        }
    except Exception as e:
        logger.error(f"Error processing API response: {e}")
        return get_fallback_response(game_state.tension)

def test_grok_connection():
    """Test the Grok API connection"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "grok-2",  # Updated model name
        "messages": [
            {"role": "user", "content": "Hello, are you working?"}
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(
            "https://api.x.ai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        logger.debug(f"Test API status: {response.status_code}")
        logger.debug(f"Test API response: {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Test API error: {e}")
        return False
