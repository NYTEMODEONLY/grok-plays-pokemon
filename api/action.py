"""
Grok Plays Pokemon - Action API

Receives preprocessed game state (screen type, OCR text) from frontend
and returns appropriate action using screen-specific prompts.
"""

from http.server import BaseHTTPRequestHandler
import os
import json
import re
import urllib.request
import urllib.error

# Import game state utilities
try:
    from .game_state import GameState, load_prompt, build_user_message
except ImportError:
    from game_state import GameState, load_prompt, build_user_message


def get_game_action(api_key: str, image_base64: str, game_state: GameState) -> dict:
    """
    Get game action from xAI Grok using screen-specific prompts.

    Args:
        api_key: xAI API key
        image_base64: Base64 encoded screenshot
        game_state: GameState object with preprocessing results

    Returns:
        Dict with action, commentary, confidence
    """

    # NOTE: Removed early-return for 'loading' screens because:
    # 1. Client-side detection may fail (WebGL canvas issues) and misclassify screens
    # 2. The screenshot sent to the AI is correct, so let AI vision decide
    # 3. AI can detect actual loading/black screens from the image itself
    # Previously: if screen_type == 'loading' and confidence > 0.7: return wait

    # Load the appropriate prompt for this screen type
    screen_prompt = load_prompt(game_state.screen_type)

    # Build compact system prompt
    system_prompt = f"""You are playing Pokemon Red/Blue/Yellow. Analyze the screenshot and choose an action.

{screen_prompt}

CONTROLS: a, b, up, down, left, right, start, select
OUTPUT: JSON only - {{"action": "<button>", "commentary": "<what you see and why>", "confidence": <0.0-1.0>}}"""

    # Build user message with context
    user_message = build_user_message(game_state)

    try:
        # Build request payload - much smaller than before
        payload = {
            "model": "grok-2-vision-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}", "detail": "high"}}
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.1  # Lower temperature for more consistent responses
        }

        # Make API request
        req = urllib.request.Request(
            "https://api.x.ai/v1/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "GrokPlaysPokemon/2.0",
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            result = json.loads(response.read().decode('utf-8'))

        text = result['choices'][0]['message']['content'].strip()

        # Parse JSON response
        data = None
        if text.startswith('{'):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                pass

        if not data:
            # Try to extract JSON from response
            match = re.search(r'\{[^{}]+\}', text)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        if not data:
            return {
                "action": "wait",
                "commentary": "Could not parse AI response",
                "confidence": 0.0,
                "retry": True,
                "raw_response": text[:200]
            }

        # Extract and validate action
        action = data.get("action", "").lower()
        commentary = data.get("commentary", "")
        confidence = float(data.get("confidence", 0.5))

        # Validate action
        valid_actions = ["a", "b", "up", "down", "left", "right", "start", "select", "wait"]
        if action not in valid_actions:
            return {
                "action": "wait",
                "commentary": f"Invalid action '{action}' returned",
                "confidence": 0.0,
                "retry": True
            }

        # Validate against game state
        validation = game_state.validate_action(action)
        if not validation['valid']:
            return {
                "action": validation.get('suggested_action', 'wait'),
                "commentary": f"Validation failed: {validation['reason']}",
                "confidence": 0.3,
                "original_action": action,
                "validation_override": True
            }

        # Check for empty commentary (sign AI didn't actually analyze)
        if not commentary or len(commentary) < 3:
            return {
                "action": "wait",
                "commentary": "No analysis provided by AI",
                "confidence": 0.0,
                "retry": True
            }

        # Detect if AI is describing wrong screen type
        ai_screen_type = detect_screen_from_commentary(commentary)
        if ai_screen_type and game_state.screen_confidence > 0.8:
            if ai_screen_type != game_state.screen_type:
                # Screen type mismatch - AI might be hallucinating
                return {
                    "action": "wait",
                    "commentary": f"Screen mismatch: detected {game_state.screen_type}, AI said {ai_screen_type}",
                    "confidence": 0.2,
                    "retry": True,
                    "mismatch": True
                }

        return {
            "action": action,
            "commentary": commentary,
            "confidence": min(1.0, max(0.0, confidence)),
            "screen_type": game_state.screen_type
        }

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode('utf-8')
        except:
            pass
        print(f"xAI HTTP Error: {e.code} - {error_body}")

        if e.code == 429:
            return {"action": "wait", "commentary": "Rate limited - waiting", "confidence": 0.0, "retry": True}
        elif e.code >= 500:
            return {"action": "wait", "commentary": "Server error - waiting", "confidence": 0.0, "retry": True}
        return {"action": "wait", "commentary": f"API Error {e.code}", "confidence": 0.0, "retry": True}

    except urllib.error.URLError as e:
        print(f"xAI URL Error: {e.reason}")
        return {"action": "wait", "commentary": "Connection error", "confidence": 0.0, "retry": True}

    except json.JSONDecodeError:
        return {"action": "wait", "commentary": "JSON parse error", "confidence": 0.0, "retry": True}

    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {"action": "wait", "commentary": f"Error: {str(e)[:50]}", "confidence": 0.0, "retry": True}


def detect_screen_from_commentary(commentary: str) -> str | None:
    """
    Try to detect what screen type the AI thinks it's looking at from its commentary.

    Returns screen type string or None if can't determine.
    """
    if not commentary:
        return None

    commentary_lower = commentary.lower()

    # Look for screen type keywords
    if any(word in commentary_lower for word in ['title screen', 'press start', 'pokemon logo']):
        return 'title'

    if any(word in commentary_lower for word in ['dialog', 'dialogue', 'text box', 'talking', 'speaking']):
        return 'dialog'

    if any(word in commentary_lower for word in ['battle', 'fighting', 'hp bar', 'attack', 'fight menu']):
        if 'move' in commentary_lower and ('select' in commentary_lower or 'choosing' in commentary_lower):
            return 'battle_move_select'
        return 'battle'

    if any(word in commentary_lower for word in ['menu', 'pokemon menu', 'item menu', 'save', 'option']):
        return 'menu'

    if any(word in commentary_lower for word in ['overworld', 'walking', 'route', 'town', 'city']):
        return 'overworld'

    if any(word in commentary_lower for word in ['name entry', 'naming', 'letter grid', 'keyboard']):
        return 'name_entry'

    if 'yes' in commentary_lower and 'no' in commentary_lower:
        return 'yes_no'

    return None


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        # Check API key
        api_key = os.getenv('XAI_API_KEY', '').strip()
        if not api_key:
            self._send_json_response({
                "action": "wait",
                "commentary": "xAI API key not configured",
                "confidence": 0.0,
                "error": "XAI_API_KEY not set",
                "retry": False
            })
            return

        # Parse request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # Extract data
        screenshot = data.get('screenshot', '')
        if not screenshot:
            self._send_json_response({
                "action": "wait",
                "commentary": "No screenshot provided",
                "confidence": 0.0,
                "retry": True
            })
            return

        # Build game state from frontend preprocessing
        state_data = {
            'screen_type': data.get('screen_type', 'unknown'),
            'screen_confidence': data.get('screen_confidence', 0.0),
            'ocr_text': data.get('ocr_text', ''),
            'recent_actions': data.get('recent_actions', []),
            'location': data.get('location', 'Unknown'),
            'badges': data.get('badges', 0),
            'pokemon_team': data.get('pokemon_team', []),
        }

        game_state = GameState(state_data)

        # Get AI action
        result = get_game_action(api_key, screenshot, game_state)

        self._send_json_response(result)

    def _send_json_response(self, data: dict):
        """Send JSON response with CORS headers."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
