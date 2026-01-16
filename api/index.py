"""
Vercel Serverless API for Grok Plays Pokemon
This handles AI decision-making via the xAI API.
"""

import os
import json
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Try to import openai for xAI API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def get_xai_client():
    """Get xAI client instance."""
    api_key = os.getenv('XAI_API_KEY')
    if not api_key or not OPENAI_AVAILABLE:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")


def get_game_action(client, image_base64, game_state, recent_actions=None, context=None):
    """Get game action from Grok AI."""
    system_prompt = """You are Grok, an AI playing Pokemon Red/Blue/Yellow on a Game Boy. Your goal is to complete the game - catch Pokemon, defeat gym leaders, and become the Pokemon Champion.

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

    user_prompt_parts = ["Current game state:"]
    if game_state:
        if game_state.get("location"):
            user_prompt_parts.append(f"- Location: {game_state['location']}")
        if game_state.get("pokemon_team"):
            team_str = ", ".join([f"{p['name']} Lv{p['level']}" for p in game_state['pokemon_team']])
            user_prompt_parts.append(f"- Team: {team_str}")
        if game_state.get("badges") is not None:
            user_prompt_parts.append(f"- Badges: {game_state['badges']}/8")

    if recent_actions:
        user_prompt_parts.append(f"\nRecent actions: {' -> '.join(recent_actions[-10:])}")

    if context:
        user_prompt_parts.append(f"\nContext: {context}")

    user_prompt_parts.append("\nLook at the screenshot and decide the next action. Respond with JSON only.")

    try:
        response = client.chat.completions.create(
            model="grok-2-vision-1212",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "\n".join(user_prompt_parts)},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.7
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON from response
        import re
        if response_text.startswith('{'):
            data = json.loads(response_text)
        else:
            json_match = re.search(r'\{[^{}]*\}', response_text)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"action": "a", "commentary": "Parsing error", "confidence": 0.1}

        action = data.get("action", "a").lower()
        valid_actions = ["a", "b", "up", "down", "left", "right", "start", "select"]
        if action not in valid_actions:
            action = "a"

        return {
            "action": action,
            "commentary": data.get("commentary", "Making a move..."),
            "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.5))))
        }

    except Exception as e:
        return {
            "action": "a",
            "commentary": f"API error: {str(e)[:50]}",
            "confidence": 0.0
        }


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/health':
            self._send_json({"status": "ok", "api_available": OPENAI_AVAILABLE and bool(os.getenv('XAI_API_KEY'))})
        elif path == '/api/status':
            self._send_json({
                "status": "ready",
                "api_configured": bool(os.getenv('XAI_API_KEY')),
                "message": "Grok Plays Pokemon API is ready"
            })
        else:
            self._send_html()

    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'

        try:
            data = json.loads(body)
        except:
            data = {}

        if path == '/api/action':
            self._handle_action_request(data)
        elif path == '/api/analyze':
            self._handle_analyze_request(data)
        else:
            self._send_json({"error": "Not found"}, 404)

    def _handle_action_request(self, data):
        """Handle AI action request."""
        client = get_xai_client()

        if not client:
            self._send_json({
                "error": "xAI API not configured",
                "action": "a",
                "commentary": "API key not set - using default",
                "confidence": 0.0
            })
            return

        image_base64 = data.get('screenshot', '')
        game_state = data.get('game_state', {})
        recent_actions = data.get('recent_actions', [])
        context = data.get('context', None)

        if not image_base64:
            self._send_json({
                "error": "No screenshot provided",
                "action": "a",
                "commentary": "No image to analyze",
                "confidence": 0.0
            })
            return

        result = get_game_action(client, image_base64, game_state, recent_actions, context)
        self._send_json(result)

    def _handle_analyze_request(self, data):
        """Handle screen analysis request."""
        client = get_xai_client()

        if not client:
            self._send_json({"error": "xAI API not configured"})
            return

        image_base64 = data.get('screenshot', '')

        if not image_base64:
            self._send_json({"error": "No screenshot provided"})
            return

        try:
            response = client.chat.completions.create(
                model="grok-2-vision-1212",
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze this Pokemon game screenshot. Identify: screen type (battle/overworld/menu/dialogue/title), what's happening, and any important details. Respond with JSON: {\"screen_type\": \"type\", \"description\": \"brief desc\", \"details\": \"important info\"}"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's on this screen?"},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                        ]
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )

            response_text = response.choices[0].message.content.strip()
            try:
                if response_text.startswith('{'):
                    result = json.loads(response_text)
                else:
                    import re
                    match = re.search(r'\{[^{}]*\}', response_text)
                    result = json.loads(match.group()) if match else {"description": response_text}
            except:
                result = {"description": response_text[:200]}

            self._send_json(result)

        except Exception as e:
            self._send_json({"error": str(e)})

    def _send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html(self):
        """Send the main HTML page."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Grok Plays Pokemon</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: system-ui; max-width: 800px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #fff; }
        h1 { color: #00ff88; }
        .info { background: #16213e; padding: 20px; border-radius: 10px; margin: 20px 0; }
        a { color: #00ff88; }
    </style>
</head>
<body>
    <h1>Grok Plays Pokemon API</h1>
    <div class="info">
        <h2>Status: Ready</h2>
        <p>This is the API endpoint for Grok Plays Pokemon.</p>
        <p>For the full experience with the Game Boy emulator, run the application locally:</p>
        <pre>python app.py</pre>
        <p>Or visit the <a href="https://github.com/NYTEMODEONLY/grok-plays-pokemon">GitHub repository</a> for instructions.</p>
    </div>
    <div class="info">
        <h2>API Endpoints</h2>
        <ul>
            <li><code>GET /api/health</code> - Health check</li>
            <li><code>GET /api/status</code> - API status</li>
            <li><code>POST /api/action</code> - Get AI action for game state</li>
            <li><code>POST /api/analyze</code> - Analyze game screenshot</li>
        </ul>
    </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
