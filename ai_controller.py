#!/usr/bin/env python3
"""
AI Controller Framework for Grok Plays Pokémon
This module provides a framework for multiple AIs to control the game.
"""

import time
import requests
import json
import logging
import random
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:5000/api"

class PokemonAI(ABC):
    """
    Abstract base class for AI controllers.
    Each AI implementation should extend this class.
    """
    
    def __init__(self, name):
        """Initialize the AI controller."""
        self.name = name
        self.game_state = {}
        self.screen_state = None
        self.previous_actions = []
        self.current_role = "player"  # "player" or "pokemon"
    
    @abstractmethod
    def decide_action(self, game_state, screen_state=None, role="player"):
        """
        Decide what action to take based on the current game state.
        
        Args:
            game_state: Current state of the game (Pokémon, items, location, etc.)
            screen_state: Optional screenshot or screen data
            role: Current role ("player" or "pokemon")
            
        Returns:
            action: The action to take (e.g., "a", "b", "up", etc.)
            commentary: Commentary about the decision
        """
        pass
    
    def update_state(self, game_state, screen_state=None):
        """Update the AI's knowledge of the game state."""
        self.game_state = game_state
        self.screen_state = screen_state
    
    def record_action(self, action):
        """Record an action taken by the AI."""
        self.previous_actions.append(action)
        # Keep only the last 20 actions
        if len(self.previous_actions) > 20:
            self.previous_actions.pop(0)
    
    def set_role(self, role):
        """Set the current role of the AI."""
        if role in ["player", "pokemon"]:
            self.current_role = role
        else:
            logger.warning(f"Invalid role: {role}. Must be 'player' or 'pokemon'.")


class GrokAI(PokemonAI):
    """
    Grok AI implementation for playing Pokémon.
    """
    
    def __init__(self):
        """Initialize the Grok AI."""
        super().__init__("Grok")
    
    def decide_action(self, game_state, screen_state=None, role="player"):
        """Grok's decision-making logic."""
        # This is a simplified placeholder for Grok's actual decision-making
        # In a real implementation, this would connect to Grok's API
        
        self.update_state(game_state, screen_state)
        
        # Different logic based on role
        if role == "player":
            return self._decide_player_action()
        elif role == "pokemon":
            return self._decide_pokemon_action()
        
    def _decide_player_action(self):
        """Decide actions for player movement and exploration."""
        location = self.game_state.get("location", "")
        
        # Starting the game
        if location == "PALLET TOWN" and not self.previous_actions:
            return "a", "Let's start our Pokémon adventure!"
        
        # Choose starter Pokémon
        if "SQUIRTLE" not in str(self.game_state) and len(self.previous_actions) < 15:
            # Try to navigate to and select Squirtle
            if random.random() < 0.5:
                return "a", "Exploring the options..."
            else:
                return random.choice(["up", "down", "left", "right"]), "Looking for Squirtle..."
        
        # Basic exploration logic
        if random.random() < 0.3:
            # Talk to NPCs or interact with objects
            return "a", "Let's see what this person has to say!"
        else:
            # Move around
            direction = random.choice(["up", "down", "left", "right"])
            return direction, f"Exploring in the {direction} direction."
    
    def _decide_pokemon_action(self):
        """Decide actions during Pokémon battles."""
        # Get current Pokémon info
        pokemon_team = self.game_state.get("pokemon_team", [])
        
        if not pokemon_team:
            return "a", "Let's see what happens next in this battle!"
        
        # Check if we should use an item
        current_pokemon = pokemon_team[0]
        hp_percent = current_pokemon.get("hp", 0) / current_pokemon.get("max_hp", 1)
        
        if hp_percent < 0.3:
            return "b", "Our Pokémon is low on health! Let's use a potion."
        
        # Choose a move based on simple type advantage (placeholder logic)
        return "a", "Using our strongest move! It should be super effective!"


class ClaudeAI(PokemonAI):
    """
    Claude AI implementation for playing Pokémon.
    """
    
    def __init__(self):
        """Initialize the Claude AI."""
        super().__init__("Claude")
        self.strategy = "balanced"  # balanced, aggressive, defensive
    
    def decide_action(self, game_state, screen_state=None, role="player"):
        """Claude's decision-making logic."""
        # This is a simplified placeholder for Claude's actual decision-making
        # In a real implementation, this would connect to Claude's API
        
        self.update_state(game_state, screen_state)
        
        # Different logic based on role
        if role == "player":
            return self._decide_player_action()
        elif role == "pokemon":
            return self._decide_pokemon_action()
    
    def _decide_player_action(self):
        """Claude's player movement and exploration strategy."""
        location = self.game_state.get("location", "")
        
        # Starting the game
        if location == "PALLET TOWN" and not self.previous_actions:
            return "a", "I'm excited to start this Pokémon journey! Let's see what awaits us."
        
        # Choose starter Pokémon (Claude prefers Bulbasaur)
        if "BULBASAUR" not in str(self.game_state) and len(self.previous_actions) < 15:
            # Navigate to Bulbasaur
            if "right" not in self.previous_actions[-3:] if self.previous_actions else True:
                return "left", "I think Bulbasaur is an excellent strategic choice for the early gyms."
            else:
                return "a", "Bulbasaur is my choice - great for the first two gyms!"
        
        # More methodical exploration than Grok
        recent_moves = self.previous_actions[-5:] if self.previous_actions else []
        
        # Avoid backtracking immediately
        if recent_moves and recent_moves[-1] == "up":
            avoid = "down"
        elif recent_moves and recent_moves[-1] == "down":
            avoid = "up"
        elif recent_moves and recent_moves[-1] == "left":
            avoid = "right"
        elif recent_moves and recent_moves[-1] == "right":
            avoid = "left"
        else:
            avoid = None
        
        # Systematic exploration
        if avoid:
            options = ["up", "down", "left", "right"]
            options.remove(avoid)
            direction = random.choice(options)
        else:
            direction = random.choice(["up", "down", "left", "right"])
        
        if random.random() < 0.25:
            return "a", "I should check if there's anything interesting here."
        else:
            return direction, f"Let's explore {direction}ward and see what we find."
    
    def _decide_pokemon_action(self):
        """Claude's battle strategy."""
        # Get current Pokémon info
        pokemon_team = self.game_state.get("pokemon_team", [])
        
        if not pokemon_team:
            return "a", "Analyzing the battle situation..."
        
        # More strategic battle approach
        current_pokemon = pokemon_team[0]
        hp_percent = current_pokemon.get("hp", 0) / current_pokemon.get("max_hp", 1)
        
        # Consider switching if health is low
        if hp_percent < 0.2 and len(pokemon_team) > 1:
            if random.random() < 0.7:  # 70% chance to switch
                return "b", "Strategic retreat - let's switch to a healthier Pokémon."
        
        # Type-based strategy (placeholder)
        if random.random() < 0.4:
            return "down", "Let's select a move with type advantage."
        else:
            return "a", "This move should be effective based on type matchups."


class AIManager:
    """
    Manager class for handling multiple AIs and coordinating their actions.
    """
    
    def __init__(self):
        """Initialize the AI Manager."""
        self.grok = GrokAI()
        self.claude = ClaudeAI()
        self.active_player_ai = self.grok  # Default player AI
        self.active_pokemon_ai = self.claude  # Default Pokémon AI
        self.dual_mode = False  # Whether dual AI mode is enabled
    
    def set_active_player_ai(self, ai_name):
        """Set the active player AI."""
        if ai_name.lower() == "grok":
            self.active_player_ai = self.grok
        elif ai_name.lower() == "claude":
            self.active_player_ai = self.claude
        else:
            logger.warning(f"Unknown AI: {ai_name}. Using Grok as default.")
            self.active_player_ai = self.grok
        
        logger.info(f"Set active player AI to {self.active_player_ai.name}")
    
    def set_active_pokemon_ai(self, ai_name):
        """Set the active Pokémon AI."""
        if ai_name.lower() == "grok":
            self.active_pokemon_ai = self.grok
        elif ai_name.lower() == "claude":
            self.active_pokemon_ai = self.claude
        else:
            logger.warning(f"Unknown AI: {ai_name}. Using Claude as default.")
            self.active_pokemon_ai = self.claude
        
        logger.info(f"Set active Pokémon AI to {self.active_pokemon_ai.name}")
    
    def set_dual_mode(self, enabled):
        """Enable or disable dual AI mode."""
        self.dual_mode = enabled
        logger.info(f"Dual AI mode {'enabled' if enabled else 'disabled'}")
    
    def get_action(self, game_state, screen_state=None):
        """
        Get the next action from the appropriate AI based on game state.
        
        In dual mode, this selects between player AI and Pokémon AI based on
        whether the game is in a battle or not.
        
        In single mode, it always uses the player AI regardless of game state.
        """
        # Determine if we're in a battle
        in_battle = self._is_in_battle(game_state)
        
        if self.dual_mode and in_battle:
            # We're in a battle, use the Pokémon AI
            ai = self.active_pokemon_ai
            role = "pokemon"
            prefix = f"[{ai.name} as Pokémon] "
        else:
            # We're exploring or dual mode is off, use the player AI
            ai = self.active_player_ai
            role = "player" if not in_battle else "pokemon"  # Still specify the correct role even in single mode
            
            if self.dual_mode:
                prefix = f"[{ai.name} as Trainer] "
            else:
                # In single mode, make it clear if we're in battle or not
                prefix = f"[{ai.name}] " if not in_battle else f"[{ai.name} in Battle] "
        
        # Get the AI's decision
        action, commentary = ai.decide_action(game_state, screen_state, role)
        
        # Record the action
        ai.record_action(action)
        
        # Add AI name prefix to commentary
        commentary = prefix + commentary
        
        return action, commentary
    
    def _is_in_battle(self, game_state):
        """Determine if the game is currently in a battle."""
        # This is a simplified placeholder - would need game-specific logic
        # Could check for battle indicator in game_state or screen_state
        # For now, we'll use a simple heuristic
        if "battle" in str(game_state).lower() or game_state.get("screen", "") == "battle":
            return True
        return False


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

def start_game():
    """Start the game."""
    try:
        response = requests.get(f"{API_BASE_URL}/start_game")
        return response.json()
    except Exception as e:
        logger.error(f"Error starting game: {e}")
        return {"success": False, "error": str(e)}

def demo():
    """Demo of the AI controller framework."""
    logger.info("Starting AI controller demo")
    
    # Create AI manager
    manager = AIManager()
    
    # Example: Set active AIs and mode
    manager.set_active_player_ai("grok")
    manager.set_active_pokemon_ai("claude")
    manager.set_dual_mode(True)
    
    # Start the game if not running
    status = get_game_status()
    if status.get("status") != "running":
        logger.info("Starting the game")
        start_game()
        time.sleep(2)  # Wait for game to initialize
    
    # Run the AIs for a few steps
    for _ in range(10):
        # Get current game state
        state = get_game_state()
        
        # Get AI's decision
        action, commentary = manager.get_action(state)
        
        # Execute the action
        execute_action(action, commentary)
        
        # Wait a bit before next action
        time.sleep(1)
    
    logger.info("AI controller demo completed")

if __name__ == "__main__":
    demo() 