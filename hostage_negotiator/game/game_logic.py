import logging
import random
from dataclasses import dataclass
from datetime import datetime
from .scenario_manager import Scenario

logging.basicConfig(level=logging.DEBUG)

@dataclass
class GameState:
    turn: int = 1
    tension: int = 7  # Replaces mood (1-10 scale)
    trust: int = 3    # New trust meter (1-10 scale)
    hostages: int = 5
    messages: list = None
    game_over: bool = False
    success: bool = False
    scenario: Scenario = None
    good_choice_streak: int = 0
    promises_kept: list = None
    rapport: int = 0
    hostages_released: int = 0
    surrender_offered: bool = False
    poor_choices: int = 0
    similar_inputs_count: int = 0
    last_input_type: str = None
    emotional_appeals_count: int = 0

    def __post_init__(self):
        """Initialize message list if not provided"""
        if self.messages is None:
            self.messages = []
            self.messages.extend([
                ("system", "Initial contact has been established. The suspect has provided proof of life for all hostages."),
                ("system", "Your task now is to negotiate for a peaceful resolution.")
            ])
        if self.promises_kept is None:
            self.promises_kept = []

    def detect_response_type(self, text):
        """Enhanced response type detection with anti-exploit mechanics"""
        text = text.lower()

        # Track repeated patterns for anti-exploit
        if self.last_input_type and text.strip() == self.last_input_type:
            self.similar_inputs_count += 1
        else:
            self.similar_inputs_count = 0
            self.last_input_type = text.strip()

        # Check for surrender acceptance
        if self.surrender_offered and any(word in text for word in ["yes", "accept", "agree", "okay", "ok"]):
            return 'accept_surrender'

        # Emotional Appeal Detection
        emotional_keywords = ["please", "understand", "feel", "need", "help", "care", "trust", "believe"]
        if any(word in text for word in emotional_keywords):
            self.emotional_appeals_count += 1
            if self.emotional_appeals_count <= 2:
                return 'empathy'
            return 'overused_emotion'

        # Calibrated Questions
        if any(word + " " in text for word in ["how", "what", "tell", "explain"]) and "?" in text:
            return 'calibrated'

        # Bargaining Detection
        if any(phrase in text for phrase in [
            "i'll get you", "i can get you", "i will get",
            "let me get", "i'll have", "i can arrange", "offer",
            "deal", "trade", "exchange"
        ]):
            return 'action'

        # Mirroring Detection
        last_suspect_message = next((msg[1].lower() for msg in reversed(self.messages)
                                    if msg[0] == 'suspect'), '')
        words = last_suspect_message.split()
        if len(words) >= 3:
            key_phrases = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
            if any(phrase in text for phrase in key_phrases):
                return 'mirror'

        # Hostage Release Request
        if any(phrase in text for phrase in [
            "release the hostages", "let them go", "free the hostages",
            "release them", "set them free"
        ]):
            return 'release_request'

        # Mistake Detection
        if any(word in text for word in ["no", "won't", "can't", "never", "don't", "stop"]):
            return 'mistake'

        # Random humor/irrationality (20% chance)
        if random.random() < 0.2:
            return 'unpredictable'

        return 'neutral'

    def adjust_state(self, response_type):
        """Enhanced state adjustment with trust and tension mechanics"""
        logging.debug(f"Adjusting state for response type: {response_type}")

        # Base changes for each response type (tension, trust, score)
        changes = {
            'empathy': {'tension': -2, 'trust': 2, 'score': 4},
            'mirror': {'tension': -1, 'trust': 2, 'score': 3},
            'action': {'tension': -2 if self.trust > 5 else 2, 'trust': 2 if self.tension <= 7 else -1, 'score': 4},
            'calibrated': {'tension': -2, 'trust': 3, 'score': 5},
            'release_request': {'tension': 3 if self.trust < 5 else -1, 'trust': -2 if self.tension >= 8 else 1, 'score': -3},
            'accept_surrender': {'tension': 0, 'trust': 0, 'score': 0},
            'neutral': {'tension': 1, 'trust': -1, 'score': -2},
            'mistake': {'tension': 3, 'trust': -3, 'score': -5},
            'overused_emotion': {'tension': 2, 'trust': -2, 'score': -4},
            'unpredictable': {'tension': random.choice([-1, 1]), 'trust': random.choice([-1, 1]), 'score': 2}
        }

        # Get base changes
        change = changes.get(response_type, {'tension': 0, 'trust': 0, 'score': 0})

        # Apply anti-exploit mechanics
        if self.similar_inputs_count >= 3:
            change['tension'] += 2
            change['trust'] -= 2
            self.messages.append(("system", "Warning: Repeating the same approach may escalate the situation."))

        # Process realistic consequences
        self.tension = max(1, min(10, self.tension + change['tension']))
        self.trust = max(1, min(10, self.trust + change['trust']))

        # Add randomized responses (20% chance)
        if random.random() < 0.2:
            random_responses = [
                "This negotiation's getting interesting...",
                "You think you've got me figured out?",
                "Maybe I'll change my mind about everything!",
                "Let's see if you can keep up..."
            ]
            self.messages.append(("suspect", random.choice(random_responses)))

        # Offer surrender at high trust and low tension
        if self.tension <= 2 and self.trust >= 8 and not self.surrender_offered:
            self.surrender_offered = True
            self.messages.append(("system", "The suspect is ready to surrender. Do you accept?"))

        # Track poor tactical choices
        if response_type in ['mistake', 'neutral', 'overused_emotion']:
            self.poor_choices += 1

    def release_hostages(self, surrender=False):
        """Handle the release of hostages"""
        if surrender:
            self.hostages_released = self.hostages
            self.game_over = True
            self.success = True
            self.messages.append(("system", "The suspect has surrendered and released all hostages. Negotiation successful!"))
        else:
            self.messages.append(("system", "The suspect isn't ready to release hostages yet. Keep building trust."))

    def process_ai_response(self, response):
        """Process AI response and update game state"""
        try:
            if not response:
                logging.warning("Received empty AI response, using fallback")
                response = "I understand your message. Let's continue our negotiation."

            self.messages.append(("suspect", response))
            self.turn += 1

            if self.tension >= 9:
                self.messages.append(("system", "Warning: Suspect is becoming extremely agitated! One more mistake could be catastrophic."))

            if self.tension >= 10:
                self.game_over = True
                self.success = False
                self.hostages -= 1
                self.messages.append(("system", "The situation has escalated beyond control. A hostage has been harmed."))
            elif self.turn >= 10:
                # Win only if tension is very low and trust is high
                if self.tension <= 2 and self.trust >= 7:
                    self.game_over = True
                    self.success = True
                    self.messages.append(("system", "The suspect's resolve has completely broken. Negotiation successful!"))
                else:
                    self.game_over = True
                    self.success = False
                    self.messages.append(("system", "Time has run out. Negotiation failed."))
        except Exception as e:
            logging.error(f"Error processing AI response: {str(e)}")
            self.messages.append(("system", "There was an issue with the negotiation. Please try again."))
            return False
        return True

    def is_game_over(self):
        return self.game_over

    def is_success(self):
        return self.success

    def to_dict(self):
        """Convert GameState to dictionary for session storage"""
        scenario_dict = None
        if self.scenario:
            scenario_dict = {
                'name': self.scenario.name,
                'setting': self.scenario.setting,
                'suspect': self.scenario.suspect,
                'initial_mood': self.scenario.initial_mood,
                'hostages': self.scenario.hostages,
                'opening_dialogue': self.scenario.opening_dialogue,
                'demand': self.scenario.demand,
                'goal': self.scenario.goal,
                'suspect_type': self.scenario.suspect_type or 'pragmatic'  # Ensure default value
            }

        return {
            'turn': self.turn,
            'tension': self.tension,
            'trust': self.trust,
            'hostages': self.hostages,
            'messages': self.messages,
            'game_over': self.game_over,
            'success': self.success,
            'scenario': scenario_dict,
            'good_choice_streak': self.good_choice_streak,
            'promises_kept': self.promises_kept,
            'rapport': self.rapport,
            'hostages_released': self.hostages_released,
            'surrender_offered': self.surrender_offered,
            'poor_choices': self.poor_choices,
            'similar_inputs_count': self.similar_inputs_count,
            'last_input_type': self.last_input_type,
            'emotional_appeals_count': self.emotional_appeals_count
        }

    @classmethod
    def from_dict(cls, data):
        """Create GameState from dictionary, handling missing fields gracefully"""
        if not data:
            return None

        # Extract scenario data safely
        scenario_data = data.pop('scenario', None)

        # Create instance with remaining data
        instance = cls(**{k: v for k, v in data.items() if hasattr(cls, k)})

        # Handle scenario separately to ensure proper initialization
        if scenario_data:
            from .scenario_manager import Scenario
            instance.scenario = Scenario(
                name=scenario_data.get('name', 'Default Scenario'),
                setting=scenario_data.get('setting', 'Unknown'),
                suspect=scenario_data.get('suspect', 'Unknown'),
                initial_mood=scenario_data.get('initial_mood', 7),
                hostages=scenario_data.get('hostages', 5),
                opening_dialogue=scenario_data.get('opening_dialogue', ''),
                demand=scenario_data.get('demand', ''),
                goal=scenario_data.get('goal', 'Negotiate for peaceful resolution'),
                suspect_type=scenario_data.get('suspect_type', 'pragmatic')
            )
        else:
            # Provide a default scenario if none exists
            from .scenario_manager import ScenarioManager
            instance.scenario = ScenarioManager.get_daily_scenario()

        return instance

def calculate_game_score(game_state):
    """Calculate the final game score using the updated scoring system"""
    if not game_state.game_over:
        return None

    # 1. Trust Building Score (35% of total)
    trust_score = (game_state.trust / 10) * 35

    # 2. Tension Management Score (30% of total)
    initial_tension = game_state.scenario.initial_mood  # Using initial mood as initial tension
    tension_reduction = ((initial_tension - game_state.tension) / initial_tension) * 30
    tension_score = max(0, tension_reduction)

    # 3. Tactical Effectiveness Score (20% of total)
    tactical_score = 20  # Start with full points
    poor_choices = getattr(game_state, 'poor_choices', 0)
    similar_inputs = getattr(game_state, 'similar_inputs_count', 0)

    # Deduct points for poor tactical choices
    tactical_score = max(0, tactical_score - (poor_choices * 4))  # -4 points per poor choice
    tactical_score = max(0, tactical_score - (similar_inputs * 2))  # -2 points for repetitive inputs

    # 4. Negotiation Efficiency Score (15% of total)
    if game_state.turn <= 5:  # Perfect efficiency
        efficiency_score = 15
    elif game_state.turn <= 7:  # Good efficiency
        efficiency_score = 12
    elif game_state.turn <= 9:  # Acceptable efficiency
        efficiency_score = 8
    else:  # Maximum turns used
        efficiency_score = 5

    # Calculate total score and scale to 1-10
    total_score = trust_score + tension_score + tactical_score + efficiency_score
    final_score = max(1, min(10, total_score / 10))  # Scale and clamp between 1-10

    return round(final_score, 2)  # Return with 2 decimal places

def process_turn(game_state, choice):
    """Process a turn based on player's choice"""
    logging.debug(f"Processing turn with choice: {choice}")

    # Process the turn
    game_state.messages.append(("player", choice))
    response_type = game_state.detect_response_type(choice)
    logging.debug(f"Detected response type: {response_type}")
    game_state.adjust_state(response_type)

    return True, "Turn processed successfully"

def save_game_score(user_id, game_state):
    """Save the game score to the database"""
    from models import Score, db
    import uuid

    score = calculate_game_score(game_state)
    if score is None:
        return None

    # Only save scores for authenticated users
    if user_id is None:
        return None

    try:
        new_score = Score(
            user_id=user_id,
            score=score,
            scenario_name=game_state.scenario.name,
            is_daily=True  # Mark as daily score
        )

        db.session.add(new_score)
        db.session.commit()

        return new_score
    except Exception as e:
        logging.error(f"Error saving score: {str(e)}")
        db.session.rollback()
        return None

def release_hostages(self, surrender=False):
    """Handle the release of hostages"""
    logging.debug(f"Releasing hostages, surrender={surrender}")
    if surrender:
        self.hostages_released = self.hostages
        self.game_over = True
        self.success = True
        self.messages.append(("system", "The suspect has surrendered and released all hostages. Negotiation successful!"))
    else:
        self.messages.append(("system", "The suspect isn't ready to release hostages yet. Keep building trust."))

def requires_login(self):
    """Login is now optional"""
    return False