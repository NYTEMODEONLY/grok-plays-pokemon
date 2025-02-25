#!/usr/bin/env python3
"""
Multi-AI Controller for Grok Plays Pokémon
Run this script to control the game with multiple AIs.
"""

import time
import argparse
import logging
from ai_controller import AIManager, get_game_status, get_game_state, execute_action, start_game

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Multi-AI Controller for Grok Plays Pokémon")
    
    parser.add_argument("--player", choices=["grok", "claude"], default="grok",
                      help="Which AI should control player movement (default: grok). In single mode, this AI controls everything.")
    
    parser.add_argument("--pokemon", choices=["grok", "claude"], default="claude",
                      help="Which AI should control Pokémon battles (default: claude)")
    
    parser.add_argument("--mode", choices=["single", "dual"], default="dual",
                      help="Run in single or dual AI mode (default: dual). In single mode, only the player AI is used for everything.")
    
    parser.add_argument("--steps", type=int, default=100,
                      help="Number of steps to run (default: 100)")
    
    parser.add_argument("--delay", type=float, default=1.0,
                      help="Delay between actions in seconds (default: 1.0)")
    
    return parser.parse_args()

def main():
    """Main function to run the multi-AI controller."""
    args = parse_args()
    
    logger.info(f"Starting Multi-AI Controller")
    logger.info(f"Player AI: {args.player}")
    logger.info(f"Pokémon AI: {args.pokemon}")
    logger.info(f"Mode: {args.mode}")
    
    # Create AI manager
    manager = AIManager()
    
    # Configure AIs based on arguments
    manager.set_active_player_ai(args.player)
    manager.set_active_pokemon_ai(args.pokemon)
    manager.set_dual_mode(args.mode == "dual")
    
    # Start the game if not running
    status = get_game_status()
    if status.get("status") != "running":
        logger.info("Starting the game")
        start_game()
        time.sleep(2)  # Wait for game to initialize
    
    # Run the AIs for specified steps
    logger.info(f"Running for {args.steps} steps with {args.delay}s delay")
    for step in range(args.steps):
        # Get current game state
        state = get_game_state()
        
        # Get AI's decision
        action, commentary = manager.get_action(state)
        
        # Execute the action
        result = execute_action(action, commentary)
        
        # Log the step
        logger.info(f"Step {step+1}/{args.steps}: {action} - {commentary}")
        
        # Check if action failed
        if not result.get("success", False):
            logger.warning(f"Action failed: {result.get('error', 'Unknown error')}")
        
        # Wait before next action
        time.sleep(args.delay)
    
    logger.info("Multi-AI controller run completed")

if __name__ == "__main__":
    main() 