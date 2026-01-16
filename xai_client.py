#!/usr/bin/env python3
"""
xAI/Grok API Client for Pokemon Gameplay
This module handles communication with the xAI API for game decisions.
"""

import os
import base64
import logging
import json
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to import openai (xAI uses OpenAI-compatible API)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available. Install with: pip install openai")


class XAIClient:
    """Client for interacting with xAI's Grok API."""

    def __init__(self, api_key=None):
        """
        Initialize the xAI client.

        Args:
            api_key: xAI API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        self.client = None
        self.model = "grok-2-vision-1212"  # Grok model with vision capabilities

        if not OPENAI_AVAILABLE:
            logger.error("OpenAI package not installed. Cannot initialize xAI client.")
            return

        if not self.api_key:
            logger.warning("No xAI API key provided. Set XAI_API_KEY environment variable.")
            return

        # Initialize the OpenAI client with xAI base URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        logger.info("xAI client initialized successfully")

    def is_available(self):
        """Check if the xAI client is properly configured."""
        return self.client is not None and self.api_key is not None

    def encode_image(self, image):
        """
        Encode a PIL image to base64 for API submission.

        Args:
            image: PIL Image object

        Returns:
            Base64 encoded string of the image
        """
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')

    def get_game_action(self, screenshot, game_state, recent_actions=None, context=None):
        """
        Get the next game action from Grok based on the current game state.

        Args:
            screenshot: PIL Image of the current game screen
            game_state: Dictionary containing game state information
            recent_actions: List of recent actions taken
            context: Additional context about the current situation

        Returns:
            Dictionary containing:
                - action: The button to press (a, b, up, down, left, right, start, select)
                - commentary: Grok's reasoning/thoughts about the action
                - confidence: How confident Grok is in this action (0-1)
        """
        if not self.is_available():
            logger.warning("xAI client not available, returning default action")
            return {
                "action": "a",
                "commentary": "xAI API not configured - using default action",
                "confidence": 0.0
            }

        # Encode the screenshot
        image_base64 = self.encode_image(screenshot)

        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(game_state, recent_actions, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )

            # Parse the response
            return self._parse_response(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error calling xAI API: {e}")
            return {
                "action": "a",
                "commentary": f"API error: {str(e)[:100]}",
                "confidence": 0.0
            }

    def _build_system_prompt(self):
        """Build the system prompt for Grok."""
        return """You are Grok, an AI playing Pokemon Red/Blue/Yellow on a Game Boy. Your goal is to complete the game - catch Pokemon, defeat gym leaders, and become the Pokemon Champion.

You can see the game screen and must decide what button to press next. The available buttons are:
- a: Confirm/Select/Talk/Interact
- b: Cancel/Back/Run
- up, down, left, right: Movement/Menu navigation
- start: Open menu
- select: Rarely used

IMPORTANT GUIDELINES:
1. Look at the screen carefully to understand the current situation
2. In menus, navigate to the correct option before pressing A
3. During battles, consider type advantages and Pokemon health
4. Explore thoroughly but don't get stuck in loops
5. Talk to NPCs for hints and story progression
6. Save the game periodically (Start -> Save)
7. Heal Pokemon at Pokemon Centers when needed
8. Catch wild Pokemon to build your team

RESPONSE FORMAT:
You must respond with a JSON object containing:
{
    "action": "button_name",
    "commentary": "Your reasoning (1-2 sentences max)",
    "confidence": 0.0-1.0
}

Only output the JSON, nothing else."""

    def _build_user_prompt(self, game_state, recent_actions=None, context=None):
        """Build the user prompt with game state information."""
        prompt_parts = ["Current game state:"]

        if game_state:
            if game_state.get("location"):
                prompt_parts.append(f"- Location: {game_state['location']}")
            if game_state.get("pokemon_team"):
                team_str = ", ".join([f"{p['name']} Lv{p['level']} ({p['hp']}/{p['max_hp']} HP)"
                                     for p in game_state['pokemon_team']])
                prompt_parts.append(f"- Team: {team_str}")
            if game_state.get("badges"):
                prompt_parts.append(f"- Badges: {game_state['badges']}/8")
            if game_state.get("money"):
                prompt_parts.append(f"- Money: ${game_state['money']}")

        if recent_actions:
            actions_str = " -> ".join(recent_actions[-10:])
            prompt_parts.append(f"\nRecent actions: {actions_str}")

        if context:
            prompt_parts.append(f"\nContext: {context}")

        prompt_parts.append("\nLook at the screenshot and decide the next action. Respond with JSON only.")

        return "\n".join(prompt_parts)

    def _parse_response(self, response_text):
        """Parse the API response into action details."""
        try:
            # Try to extract JSON from the response
            # Handle cases where the response might have extra text
            response_text = response_text.strip()

            # Try to find JSON in the response
            if response_text.startswith('{'):
                json_str = response_text
            else:
                # Try to find JSON block
                import re
                json_match = re.search(r'\{[^{}]*\}', response_text)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("No JSON found in response")

            data = json.loads(json_str)

            # Validate and extract fields
            action = data.get("action", "a").lower()
            valid_actions = ["a", "b", "up", "down", "left", "right", "start", "select"]
            if action not in valid_actions:
                action = "a"

            commentary = data.get("commentary", "Deciding next action...")
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            return {
                "action": action,
                "commentary": commentary,
                "confidence": confidence
            }

        except Exception as e:
            logger.warning(f"Failed to parse API response: {e}")
            logger.debug(f"Raw response: {response_text}")

            # Try to extract just the action from common response patterns
            response_lower = response_text.lower()
            for action in ["up", "down", "left", "right", "start", "select"]:
                if action in response_lower:
                    return {
                        "action": action,
                        "commentary": "Parsed from text response",
                        "confidence": 0.3
                    }

            # Default to 'a' if we can't parse
            return {
                "action": "a" if "a" in response_lower else "b",
                "commentary": "Could not parse response, guessing action",
                "confidence": 0.1
            }

    def analyze_screen(self, screenshot):
        """
        Analyze the game screen to determine the current context.

        Args:
            screenshot: PIL Image of the current game screen

        Returns:
            Dictionary with screen analysis:
                - screen_type: battle, overworld, menu, dialogue, title, etc.
                - description: What's happening on screen
                - suggested_context: Context for decision making
        """
        if not self.is_available():
            return {
                "screen_type": "unknown",
                "description": "API not available",
                "suggested_context": None
            }

        image_base64 = self.encode_image(screenshot)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze this Pokemon game screenshot and identify:
1. The screen type (battle, overworld, menu, dialogue, title, pokemon_center, pokemart, cave, building, route)
2. Brief description of what's happening
3. Any important details (enemy Pokemon, menu options, NPC text, etc.)

Respond with JSON only:
{
    "screen_type": "type",
    "description": "brief description",
    "details": "important details",
    "suggested_context": "context for next action"
}"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What's on this Pokemon game screen?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )

            response_text = response.choices[0].message.content.strip()

            try:
                if response_text.startswith('{'):
                    return json.loads(response_text)
                else:
                    import re
                    json_match = re.search(r'\{[^{}]*\}', response_text)
                    if json_match:
                        return json.loads(json_match.group())
            except:
                pass

            return {
                "screen_type": "unknown",
                "description": response_text[:200],
                "suggested_context": None
            }

        except Exception as e:
            logger.error(f"Error analyzing screen: {e}")
            return {
                "screen_type": "unknown",
                "description": f"Error: {str(e)[:100]}",
                "suggested_context": None
            }


# Singleton instance for easy access
_client_instance = None

def get_xai_client(api_key=None):
    """Get or create the xAI client singleton."""
    global _client_instance
    if _client_instance is None or api_key is not None:
        _client_instance = XAIClient(api_key)
    return _client_instance


if __name__ == "__main__":
    # Test the client
    client = get_xai_client()
    print(f"xAI client available: {client.is_available()}")

    if client.is_available():
        # Create a test image
        from PIL import Image
        test_image = Image.new('RGB', (160, 144), color='white')

        result = client.get_game_action(
            test_image,
            {"location": "PALLET TOWN", "badges": 0},
            ["a", "a", "up"],
            "Just started the game"
        )
        print(f"Test result: {result}")
