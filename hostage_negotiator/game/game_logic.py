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
    # Add these new counter attributes
    tactical_empathy_success: int = 0
    tactical_empathy_failure: int = 0
    mirroring_count: int = 0
    emotional_labeling_success: int = 0
    emotional_labeling_failure: int = 0

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

        # Check for surrender acceptance - this should be checked first
        if self.surrender_offered and any(word in text for word in ["yes", "accept", "agree", "okay", "ok"]):
            self.game_over = True
            self.success = True
            self.release_hostages(surrender=True)
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

    def get_emotional_state(self):
        if self.tension >= 7:
            return 'volatile'
        elif 4 <= self.tension <= 6:
            return 'agitated'
        elif 2 <= self.tension <= 3:
            return 'strategic'
        else:
            return 'resigned'

    def adjust_state(self, response_type):
        """Enhanced state adjustment with trust and tension mechanics"""
        logging.debug(f"Adjusting state for response type: {response_type}")

        # Base changes for each response type (tension, trust, score)
        changes = {
            'empathy': {
                'tension': -2, 
                'trust': 2,
                'tactical_empathy_success': 1
            },
            'mirror': {
                'tension': -1, 
                'trust': 2,
                'mirroring_count': 1
            },
            'emotional_label': {
                'tension': -2, 
                'trust': 2,
                'emotional_labeling_success': 1
            },
            'action': {
                'tension': -2 if self.trust > 5 else 2,
                'trust': 2 if self.tension <= 7 else -1
            },
            'calibrated': {
                'tension': -2,
                'trust': 3
            },
            'release_request': {
                'tension': 3 if self.trust < 5 else -1,
                'trust': -2 if self.tension >= 8 else 1
            },
            'accept_surrender': {
                'tension': 0,
                'trust': 0
            },
            'neutral': {
                'tension': 1,
                'trust': -1,
                'poor_choices': 1
            },
            'mistake': {
                'tension': 3,
                'trust': -3,
                'poor_choices': 1
            },
            'overused_emotion': {
                'tension': 2,
                'trust': -2,
                'emotional_appeals_count': 1
            }
        }

        change = changes.get(response_type, {'tension': 0, 'trust': 0})
        
        # Process realistic consequences
        self.tension = max(1, min(10, self.tension + change.get('tension', 0)))
        self.trust = max(1, min(10, self.trust + change.get('trust', 0)))
        
        # Update counters
        if change.get('tactical_empathy_success'):
            self.tactical_empathy_success += 1
        if change.get('mirroring_count'):
            self.mirroring_count += 1
        if change.get('emotional_labeling_success'):
            self.emotional_labeling_success += 1
        if change.get('poor_choices'):
            self.poor_choices += 1
        if change.get('emotional_appeals_count'):
            self.emotional_appeals_count += 1

        # Consider hostage release based on trust and tension
        emotional_state = self.get_emotional_state()
        if not self.game_over:
            if emotional_state == 'resigned' and self.trust >= 2:
                self.consider_hostage_release(all_hostages=True)
            elif emotional_state == 'strategic' and self.trust >= 4:
                self.consider_hostage_release()
            elif emotional_state == 'agitated' and self.trust >= 6:
                self.consider_hostage_release()
            elif emotional_state == 'volatile' and self.trust >= 8:
                self.consider_hostage_release()

        # Consider surrender
        if self.tension <= 2 and self.trust >= 8 and not self.surrender_offered:
            self.surrender_offered = True
            self.messages.append(("system", "The suspect is ready to surrender. Do you accept?"))

    def consider_hostage_release(self, all_hostages=False):
        """Consider releasing hostages based on current state"""
        if self.hostages > self.hostages_released:
            if all_hostages:
                to_release = self.hostages - self.hostages_released
            else:
                to_release = 1
            
            self.hostages_released += to_release
            self.hostages = self.hostages - to_release  # Add this line to update the hostage count
            self.messages.append(("system", f"{to_release} hostage(s) released as a sign of good faith."))
            return True
        return False

    def release_hostages(self, surrender=False):
        """Handle the release of hostages"""
        if surrender:
            self.hostages_released = self.hostages
            self.hostages = 0  # All hostages are released
            self.game_over = True
            self.success = True
            self.messages.append(("system", "The suspect has surrendered and released all hostages. Negotiation successful!"))
            return True
        else:
            self.messages.append(("system", "The suspect isn't ready to release hostages yet. Keep building trust."))
            return False

    def process_ai_response(self, response):
        """Process AI response and update game state"""
        try:
            if not response:
                logging.warning("Received empty AI response, using fallback")
                response = "I understand your message. Let's continue our negotiation."

            self.messages.append(("suspect", response))
            self.turn += 1

            # Check tension level first
            if self.tension >= 9:
                self.messages.append(("system", "Warning: Suspect is becoming extremely agitated! One more mistake could be catastrophic."))

            # Immediately end game if tension reaches max
            if self.tension >= 10:
                self.game_over = True
                self.success = False
                self.hostages -= 1  # A hostage is harmed
                self.messages.append(("system", "The situation has escalated beyond control. A hostage has been harmed."))
                return False  # Return False to indicate game should end
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
                return False  # Return False to indicate game should end
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
        return {
            'turn': self.turn,
            'tension': self.tension,
            'trust': self.trust,
            'hostages': self.hostages,
            'messages': self.messages,
            'game_over': self.game_over,
            'success': self.success,
            'scenario_id': self.scenario.id if self.scenario else None,
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
        from .models import Scenario
        instance = cls(
            turn=data['turn'],
            tension=data['tension'],
            trust=data['trust'],
            hostages=data['hostages']
        )
        instance.messages = data['messages']
        instance.game_over = data['game_over']
        instance.success = data['success']
        if data.get('scenario_id'):
            instance.scenario = Scenario.objects.get(id=data['scenario_id'])
        instance.good_choice_streak = data.get('good_choice_streak', 0)
        instance.promises_kept = data.get('promises_kept', [])
        instance.rapport = data.get('rapport', 0)
        instance.hostages_released = data.get('hostages_released', 0)
        instance.surrender_offered = data.get('surrender_offered', False)
        instance.poor_choices = data.get('poor_choices', 0)
        instance.similar_inputs_count = data.get('similar_inputs_count', 0)
        instance.last_input_type = data.get('last_input_type')
        instance.emotional_appeals_count = data.get('emotional_appeals_count', 0)
        return instance

def calculate_game_score(game_state):
    """Calculate the final game score using the updated scoring system"""
    if not game_state.game_over:
        return None

    # Base score components
    trust_score = (game_state.trust / 10) * 35  # Trust Building (35%)
    
    initial_tension = game_state.scenario.initial_mood
    tension_reduction = ((initial_tension - game_state.tension) / initial_tension) * 30
    tension_score = max(0, tension_reduction)  # Tension Management (30%)
    
    # Tactical Effectiveness (20%)
    tactical_score = 20
    tactical_score = max(0, tactical_score - (game_state.poor_choices * 4))
    tactical_score = max(0, tactical_score - (game_state.similar_inputs_count * 2))
    
    # Negotiation Efficiency (15%)
    if game_state.turn <= 5:
        efficiency_score = 15
    elif game_state.turn <= 7:
        efficiency_score = 12
    elif game_state.turn <= 9:
        efficiency_score = 8
    else:
        efficiency_score = 5

    # Calculate total score and scale to 1-10
    total_score = trust_score + tension_score + tactical_score + efficiency_score
    final_score = max(1, min(10, total_score / 10))

    return round(final_score, 2)  # Return with 2 decimal places

def process_turn(game_state, choice):
    """Process a turn based on player's choice"""
    logging.debug(f"Processing turn with choice: {choice}")
    
    # Check turn limit
    if game_state.turn >= 10:
        game_state.game_over = True
        if game_state.tension <= 2 and game_state.trust >= 7:
            game_state.success = True
            return False, "Negotiation successful!"
        else:
            game_state.success = False
            return False, "Time has run out. Negotiation failed."

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
        self.hostages = 0  # All hostages are released
        self.game_over = True
        self.success = True
        self.messages.append(("system", "The suspect has surrendered and released all hostages. Negotiation successful!"))
        return True
    else:
        self.messages.append(("system", "The suspect isn't ready to release hostages yet. Keep building trust."))
        return False

def requires_login(self):
    """Login is now optional"""
    return False
