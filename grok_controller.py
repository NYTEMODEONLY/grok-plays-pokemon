#!/usr/bin/env python3
"""
Grok Controller for Pokemon Red
This script demonstrates how Grok would control the game via API requests.
"""

import time
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:5000/api"

def get_game_status():
    """Get the current game status from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/status")
        return response.json()
    except Exception as e:
        logger.error(f"Error getting game status: {e}")
        return {"status": "error"}

def get_game_state():
    """Get the current game state from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/state")
        return response.json()
    except Exception as e:
        logger.error(f"Error getting game state: {e}")
        return {}

def execute_action(action, commentary=None):
    """Execute a single game action with optional commentary."""
    data = {"action": action}
    if commentary:
        data["commentary"] = commentary
    
    try:
        response = requests.post(f"{API_BASE_URL}/execute_action", json=data)
        result = response.json()
        if result.get("success"):
            logger.info(f"Action executed: {action}")
        else:
            logger.warning(f"Failed to execute action: {action} - {result.get('error')}")
        return result
    except Exception as e:
        logger.error(f"Error executing action: {e}")
        return {"success": False, "error": str(e)}

def execute_sequence(actions, commentary=None):
    """Execute a sequence of game actions with optional commentary."""
    data = {"actions": actions}
    if commentary:
        data["commentary"] = commentary
    
    try:
        response = requests.post(f"{API_BASE_URL}/execute_sequence", json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error executing sequence: {e}")
        return {"success": False, "error": str(e)}

def start_game():
    """Start the game."""
    try:
        response = requests.get(f"{API_BASE_URL}/start_game")
        return response.json()
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return {"success": False, "error": str(e)}

def stop_game():
    """Stop the game."""
    try:
        response = requests.get(f"{API_BASE_URL}/stop_game")
        return response.json()
    except Exception as e:
        logger.error(f"Error stopping game: {e}")
        return {"success": False, "error": str(e)}

def main():
    """Main function to demonstrate Grok's control of Pokemon Red."""
    logger.info("Grok controller starting")
    
    # Start the game if it's not already running
    status = get_game_status()
    if status.get("status") != "running":
        logger.info("Starting the game")
        start_game()
        time.sleep(2)  # Wait for game to initialize
    
    # Simple demonstration of game control with Grok's commentary
    
    # Example: Start a new game
    logger.info("Starting a new Pokemon game")
    execute_action("a", "Let's start our Pokemon adventure! I'm selecting 'New Game'.")
    time.sleep(1)
    
    # Skip through the intro dialogue
    for _ in range(10):
        execute_action("a", "Skipping through Professor Oak's introduction...")
        time.sleep(0.5)
    
    # Example: Choosing a starter Pokemon
    logger.info("Choosing Squirtle as starter")
    # Navigate to Squirtle
    execute_sequence(["down", "right"], "Looking at the starter options. I'll choose Squirtle!")
    time.sleep(1)
    
    # Select Squirtle
    execute_action("a", "Squirtle is a great Water-type starter. Strong against the first gym!")
    time.sleep(1)
    
    # Confirm selection
    execute_action("a", "Yes, I want Squirtle as my partner!")
    time.sleep(1)
    
    # Skip more dialogue
    for _ in range(5):
        execute_action("a", "Getting through the initial dialogue...")
        time.sleep(0.5)
    
    # Example: Leaving the lab and exploring
    logger.info("Leaving the lab")
    execute_sequence(["down", "down", "down", "down"], "Time to leave Oak's lab and start our journey!")
    time.sleep(1)
    
    # Explore Pallet Town
    logger.info("Exploring Pallet Town")
    execute_sequence(["left", "left", "left", "up", "up", "right"], 
                    "Exploring Pallet Town before heading to Route 1. Let's check out the houses!")
    time.sleep(1)
    
    # Check game state to see our progress
    state = get_game_state()
    logger.info(f"Current game state: {json.dumps(state, indent=2)}")
    
    # Example: Walking in the tall grass to find a Pokemon
    logger.info("Looking for wild Pokemon")
    execute_sequence(["up", "up", "up", "up"], 
                    "Let's head to Route 1 and try to find our first wild Pokemon in the tall grass!")
    time.sleep(1)
    
    # Example: In a battle
    logger.info("Simulating a battle")
    execute_action("a", "A wild Rattata appeared! This is common on Route 1 and good for early training.")
    time.sleep(1)
    
    # Select FIGHT
    execute_sequence(["a", "a"], "I'll choose FIGHT and use Tackle to weaken it.")
    time.sleep(1)
    
    # After a few turns
    execute_action("a", "Great! We won our first battle. Squirtle gained some experience!")
    time.sleep(1)
    
    # Continue the journey
    logger.info("Continuing the journey")
    execute_sequence(["up", "up", "up", "right", "right"], 
                    "Let's continue toward Viridian City. We need to train our Squirtle more.")
    
    # End the demonstration
    logger.info("Grok controller demonstration complete")
    
    # Optional: Stop the game when done
    # stop_game()

if __name__ == "__main__":
    main() 