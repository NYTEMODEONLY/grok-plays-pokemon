"""
Vercel Serverless Function: Health Check
GET /api/health - Returns API status
"""

import os
import json


def handler(request):
    """Health check endpoint."""
    api_key = os.getenv('XAI_API_KEY')

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "ok",
            "api_configured": bool(api_key),
            "message": "Grok Plays Pokemon API"
        })
    }
