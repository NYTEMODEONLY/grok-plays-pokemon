from http.server import BaseHTTPRequestHandler
import os
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        api_key = os.getenv('XAI_API_KEY')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        response = {
            "status": "ok",
            "api_configured": bool(api_key),
            "message": "Grok Plays Pokemon API"
        }

        self.wfile.write(json.dumps(response).encode())
        return
