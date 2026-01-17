"""
Game State Management for Grok Plays Pokemon

Handles tracking of game progress, recent actions, and screen state validation.
Since this runs on Vercel serverless, state is passed from frontend on each request.
"""

import json
from typing import Dict, List, Optional, Any


class GameState:
    """Manages game state validation and tracking."""

    # Valid screen types
    SCREEN_TYPES = {
        'title', 'dialog', 'battle', 'battle_move_select', 'menu',
        'overworld', 'name_entry', 'yes_no', 'loading', 'unknown'
    }

    # Valid actions
    VALID_ACTIONS = {'a', 'b', 'up', 'down', 'left', 'right', 'start', 'select', 'wait'}

    # Expected actions for screen types (primary action for each screen)
    SCREEN_EXPECTED_ACTIONS = {
        'title': {'start'},
        'dialog': {'a'},
        'battle': {'a', 'up', 'down', 'left', 'right'},
        'battle_move_select': {'a', 'up', 'down', 'left', 'right', 'b'},
        'menu': {'a', 'b', 'up', 'down'},
        'overworld': {'a', 'up', 'down', 'left', 'right', 'start'},
        'name_entry': {'a', 'up', 'down', 'left', 'right'},
        'yes_no': {'a', 'up', 'down'},
        'loading': {'wait'},
        'unknown': set(VALID_ACTIONS),
    }

    def __init__(self, state_data: Optional[Dict] = None):
        """Initialize game state from frontend data."""
        state_data = state_data or {}

        self.screen_type = state_data.get('screen_type', 'unknown')
        self.screen_confidence = state_data.get('screen_confidence', 0.0)
        self.ocr_text = state_data.get('ocr_text', '')
        self.recent_actions = state_data.get('recent_actions', [])
        self.location = state_data.get('location', 'Unknown')
        self.badges = state_data.get('badges', 0)
        self.pokemon_team = state_data.get('pokemon_team', [])

    def validate_action(self, action: str, ai_screen_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate that an AI-proposed action makes sense for the detected screen.

        Returns:
            Dict with 'valid' bool, 'reason' str, and 'suggested_action' if invalid
        """
        action = action.lower() if action else ''

        # Check if action is valid at all
        if action not in self.VALID_ACTIONS:
            return {
                'valid': False,
                'reason': f"Invalid action '{action}'",
                'suggested_action': 'wait'
            }

        # NOTE: Removed forced wait for 'loading' screens because client-side
        # detection is broken and misclassifies everything as loading.
        # Let the AI decide based on the actual screenshot.

        # Check for screen type mismatch
        if ai_screen_type and self.screen_confidence > 0.7:
            if ai_screen_type != self.screen_type and self.screen_type != 'unknown':
                # AI thinks it's a different screen than we detected
                expected = self.SCREEN_EXPECTED_ACTIONS.get(self.screen_type, set())
                if action not in expected and action != 'wait':
                    return {
                        'valid': False,
                        'reason': f"Screen mismatch: detected '{self.screen_type}' but AI said '{ai_screen_type}'",
                        'suggested_action': list(expected)[0] if expected else 'a'
                    }

        # Validate action makes sense for screen type
        expected_actions = self.SCREEN_EXPECTED_ACTIONS.get(self.screen_type, set())
        if self.screen_confidence > 0.8 and action not in expected_actions and action != 'wait':
            # High confidence screen detection but unexpected action
            # Only warn, don't reject - AI might see something we don't
            return {
                'valid': True,
                'warning': f"Unusual action '{action}' for screen type '{self.screen_type}'",
                'reason': None
            }

        return {'valid': True, 'reason': None}

    def detect_stuck_pattern(self) -> Optional[Dict[str, Any]]:
        """
        Detect if the AI is stuck in a loop.

        Returns:
            Dict with 'stuck' bool and 'suggestion' str if stuck
        """
        if len(self.recent_actions) < 3:
            return None

        last_three = self.recent_actions[-3:]
        last_five = self.recent_actions[-5:] if len(self.recent_actions) >= 5 else self.recent_actions

        # Pattern 1: Same action 3+ times
        if len(set(last_three)) == 1:
            stuck_action = last_three[0]
            suggestions = {
                'a': 'Try moving with arrows or press B',
                'b': 'Try A to confirm or arrows to navigate',
                'start': 'This might be a dialog - try A instead',
                'select': 'Try A or START instead',
                'up': 'Try A to interact or a different direction',
                'down': 'Try A to interact or a different direction',
                'left': 'Try A to interact or a different direction',
                'right': 'Try A to interact or a different direction',
            }
            return {
                'stuck': True,
                'pattern': 'same_action_repeated',
                'action': stuck_action,
                'suggestion': suggestions.get(stuck_action, 'Try a different action')
            }

        # Pattern 2: Oscillating between two actions
        if len(last_five) >= 4:
            pattern = last_five[-4:]
            if pattern[0] == pattern[2] and pattern[1] == pattern[3] and pattern[0] != pattern[1]:
                return {
                    'stuck': True,
                    'pattern': 'oscillating',
                    'actions': [pattern[0], pattern[1]],
                    'suggestion': 'Break the pattern - try A, B, or a different direction'
                }

        return None

    def get_context_hints(self) -> List[str]:
        """Generate context hints based on OCR text and state."""
        hints = []

        if not self.ocr_text:
            return hints

        ocr_upper = self.ocr_text.upper()

        # Detect specific game situations
        if 'PROF' in ocr_upper or 'OAK' in ocr_upper:
            hints.append('Prof Oak is speaking - press A to advance dialog')

        if 'YES' in ocr_upper and 'NO' in ocr_upper:
            hints.append('Yes/No choice detected - use up/down to select, A to confirm')

        if 'FIGHT' in ocr_upper:
            hints.append('Battle menu visible - FIGHT is usually top-left')

        if any(word in ocr_upper for word in ['PALLET', 'VIRIDIAN', 'PEWTER', 'CERULEAN']):
            hints.append('Town/city name detected - in overworld or reading sign')

        if 'POISON' in ocr_upper or 'BURN' in ocr_upper or 'SLEEP' in ocr_upper:
            hints.append('Status condition mentioned - may need to heal')

        if 'LEARNED' in ocr_upper:
            hints.append('Pokemon learned a move - press A to continue')

        if 'LEVEL' in ocr_upper and 'UP' in ocr_upper:
            hints.append('Level up - press A to continue')

        if 'NICKNAME' in ocr_upper:
            hints.append('Nickname prompt - select NO for faster gameplay')

        if 'ED' in ocr_upper or 'END' in ocr_upper:
            hints.append('Name entry END button detected - navigate there to confirm')

        return hints

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization."""
        return {
            'screen_type': self.screen_type,
            'screen_confidence': self.screen_confidence,
            'ocr_text': self.ocr_text,
            'recent_actions': self.recent_actions,
            'location': self.location,
            'badges': self.badges,
            'pokemon_team': self.pokemon_team,
        }


def load_prompt(screen_type: str) -> str:
    """
    Load the appropriate prompt for a screen type.

    Args:
        screen_type: The detected screen type

    Returns:
        The prompt text for that screen type
    """
    import os

    # Map screen types to prompt files
    prompt_map = {
        'title': 'title.txt',
        'dialog': 'dialog.txt',
        'battle': 'battle.txt',
        'battle_move_select': 'battle_moves.txt',
        'menu': 'menu.txt',
        'overworld': 'overworld.txt',
        'name_entry': 'name_entry.txt',
        'yes_no': 'yes_no.txt',
        'loading': 'loading.txt',
        'unknown': 'unknown.txt',
    }

    filename = prompt_map.get(screen_type, 'unknown.txt')
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', filename)

    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback minimal prompt
        return f"""Screen type: {screen_type}. Analyze the screenshot and decide the next action.
RESPOND WITH JSON: {{"action": "<button>", "commentary": "<what you see>", "confidence": <0.0-1.0>}}"""


def build_user_message(game_state: GameState) -> str:
    """Build the user message with context from game state."""
    parts = []

    # Add screen detection info
    if game_state.screen_type != 'unknown':
        parts.append(f"Detected screen type: {game_state.screen_type} (confidence: {game_state.screen_confidence:.0%})")

    # Add OCR text if available
    if game_state.ocr_text:
        # Truncate very long OCR text
        ocr_display = game_state.ocr_text[:500] if len(game_state.ocr_text) > 500 else game_state.ocr_text
        parts.append(f"Text on screen (OCR): {ocr_display}")

    # Add context hints
    hints = game_state.get_context_hints()
    if hints:
        parts.append("Hints: " + "; ".join(hints))

    # Add recent actions
    if game_state.recent_actions:
        parts.append(f"Recent actions: {' -> '.join(game_state.recent_actions[-5:])}")

    # Add stuck detection warning
    stuck = game_state.detect_stuck_pattern()
    if stuck and stuck.get('stuck'):
        parts.append(f"WARNING: Stuck pattern detected ({stuck['pattern']}). {stuck['suggestion']}")

    # Add location/progress if known
    if game_state.location != 'Unknown':
        parts.append(f"Location: {game_state.location}")

    if game_state.badges > 0:
        parts.append(f"Badges: {game_state.badges}/8")

    parts.append("\nAnalyze the screenshot and respond with JSON only.")

    return "\n".join(parts)
