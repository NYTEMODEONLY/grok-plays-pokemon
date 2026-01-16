"""
Vercel Serverless Function: Get AI Action
POST /api/action - Returns the next game action from Grok
"""

import os
import json
import re

def get_game_action(client, image_base64, game_state, recent_actions=None):
    """Get game action from Grok AI."""
    system_prompt = """You are Grok, an AI playing Pokemon Red/Blue/Yellow on a Game Boy. Your goal is to complete the game.

Available buttons: a, b, up, down, left, right, start, select

Guidelines:
- Look at the screen carefully
- In menus, navigate before pressing A
- Consider type advantages in battles
- Don't get stuck in loops - try different approaches
- Talk to NPCs, explore, catch Pokemon

Respond with JSON only:
{"action": "button", "commentary": "brief reason", "confidence": 0.0-1.0}"""

    user_parts = ["Current game state:"]
    if game_state:
        if game_state.get("location"):
            user_parts.append(f"Location: {game_state['location']}")
        if game_state.get("pokemon_team"):
            team = ", ".join([f"{p['name']} Lv{p['level']}" for p in game_state['pokemon_team'][:3]])
            user_parts.append(f"Team: {team}")
        if game_state.get("badges") is not None:
            user_parts.append(f"Badges: {game_state['badges']}/8")

    if recent_actions:
        user_parts.append(f"Recent: {' '.join(recent_actions[-5:])}")

    user_parts.append("Decide next action (JSON only):")

    try:
        response = client.chat.completions.create(
            model="grok-2-vision-1212",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "\n".join(user_parts)},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                    ]
                }
            ],
            max_tokens=200,
            temperature=0.7
        )

        text = response.choices[0].message.content.strip()

        # Parse JSON
        if text.startswith('{'):
            data = json.loads(text)
        else:
            match = re.search(r'\{[^{}]+\}', text)
            data = json.loads(match.group()) if match else {"action": "a"}

        action = data.get("action", "a").lower()
        if action not in ["a", "b", "up", "down", "left", "right", "start", "select"]:
            action = "a"

        return {
            "action": action,
            "commentary": data.get("commentary", "Making a move..."),
            "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.5))))
        }

    except Exception as e:
        return {"action": "a", "commentary": f"Error: {str(e)[:50]}", "confidence": 0.0}


def handler(request):
    """Vercel serverless handler."""
    # Handle CORS
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        }

    if request.method != "POST":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Method not allowed"})
        }

    # Check API key
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "action": "a",
                "commentary": "xAI API key not configured",
                "confidence": 0.0,
                "error": "XAI_API_KEY not set"
            })
        }

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    except ImportError:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "action": "a",
                "commentary": "OpenAI package not available",
                "confidence": 0.0,
                "error": "Missing dependency"
            })
        }

    # Parse request
    try:
        body = json.loads(request.body) if hasattr(request, 'body') else {}
    except:
        body = {}

    screenshot = body.get('screenshot', '')
    game_state = body.get('game_state', {})
    recent_actions = body.get('recent_actions', [])

    if not screenshot:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "action": "a",
                "commentary": "No screenshot provided",
                "confidence": 0.0
            })
        }

    result = get_game_action(client, screenshot, game_state, recent_actions)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(result)
    }
