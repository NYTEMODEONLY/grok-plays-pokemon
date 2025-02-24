import os
import time
import logging
from pyboy import PyBoy
from pyboy.utils import WindowEvent
import numpy as np
from PIL import Image
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define button mapping
BUTTON_MAP = {
    "a": WindowEvent.PRESS_BUTTON_A,
    "b": WindowEvent.PRESS_BUTTON_B,
    "start": WindowEvent.PRESS_BUTTON_START,
    "select": WindowEvent.PRESS_BUTTON_SELECT,
    "up": WindowEvent.PRESS_ARROW_UP,
    "down": WindowEvent.PRESS_ARROW_DOWN,
    "left": WindowEvent.PRESS_ARROW_LEFT,
    "right": WindowEvent.PRESS_ARROW_RIGHT
}

BUTTON_RELEASE_MAP = {
    "a": WindowEvent.RELEASE_BUTTON_A,
    "b": WindowEvent.RELEASE_BUTTON_B,
    "start": WindowEvent.RELEASE_BUTTON_START,
    "select": WindowEvent.RELEASE_BUTTON_SELECT,
    "up": WindowEvent.RELEASE_ARROW_UP,
    "down": WindowEvent.RELEASE_ARROW_DOWN,
    "left": WindowEvent.RELEASE_ARROW_LEFT,
    "right": WindowEvent.RELEASE_ARROW_RIGHT
}

class PokemonEmulator:
    def __init__(self, rom_path):
        """Initialize the Pokemon emulator with the specified ROM."""
        if not os.path.exists(rom_path):
            raise FileNotFoundError(f"ROM file not found: {rom_path}")
        
        logger.info(f"Initializing emulator with ROM: {rom_path}")
        self.rom_path = rom_path
        self.pyboy = PyBoy(rom_path, game_wrapper=True)
        self.game = self.pyboy.game_wrapper()
        self.screen_buffer = []
        self.last_screenshot = None
        self.frame_count = 0
        self.is_running = False
        
        # Game state tracking
        self.current_state = {
            "pokemon_team": [],
            "items": [],
            "location": "Unknown",
            "badges": 0,
            "money": 0,
            "current_pokemon": None
        }
        
        logger.info("Emulator initialized successfully")

    def start(self):
        """Start the emulator."""
        if not self.is_running:
            logger.info("Starting emulator")
            self.is_running = True
    
    def stop(self):
        """Stop the emulator."""
        if self.is_running:
            logger.info("Stopping emulator")
            self.is_running = False
            self.pyboy.stop()
    
    def get_screenshot(self):
        """Get the current screenshot of the game."""
        screen_image = self.pyboy.screen_image()
        self.last_screenshot = screen_image
        return screen_image
    
    def get_screen_ndarray(self):
        """Get the current screen as a numpy array."""
        return np.array(self.get_screenshot())
    
    def save_screenshot(self, path):
        """Save the current screenshot to a file."""
        self.get_screenshot().save(path)
        logger.info(f"Screenshot saved to {path}")
    
    def execute_action(self, action):
        """Execute a game action (button press)."""
        if action not in BUTTON_MAP:
            logger.warning(f"Unknown action: {action}")
            return False
        
        logger.info(f"Executing action: {action}")
        self.pyboy.send_input(BUTTON_MAP[action])
        self.tick(5)  # Small delay after button press
        self.pyboy.send_input(BUTTON_RELEASE_MAP[action])
        self.tick(5)  # Small delay after button release
        return True
    
    def execute_sequence(self, actions, delay=10):
        """Execute a sequence of actions with delays between them."""
        logger.info(f"Executing sequence: {actions}")
        results = []
        for action in actions:
            result = self.execute_action(action)
            results.append(result)
            self.tick(delay)
        return results
    
    def tick(self, frames=1):
        """Advance the emulator by a number of frames."""
        for _ in range(frames):
            self.pyboy.tick()
            self.frame_count += 1

    def run_for_seconds(self, seconds):
        """Run the emulator for a specified number of seconds."""
        fps = 60
        frames = int(seconds * fps)
        logger.info(f"Running for {seconds} seconds ({frames} frames)")
        self.tick(frames)
    
    def update_game_state(self):
        """Update the game state information."""
        # This is a placeholder - implementing actual game state extraction
        # would require deeper integration with PyBoy and game memory reading
        
        # For demo purposes, we'll just update with placeholder data
        logger.info("Updating game state")
        
        # In a real implementation, we would read memory locations to get:
        # - Current Pokémon team (species, levels, HP, moves)
        # - Items in inventory
        # - Current location (map ID)
        # - Badges collected
        # - Money
        # - Current battle state if in battle
        
        # For now, just return placeholder data
        self.current_state = {
            "pokemon_team": [
                {"name": "SQUIRTLE", "level": 5, "hp": 20, "max_hp": 20},
            ],
            "items": [
                {"name": "Potion", "count": 1},
                {"name": "Poké Ball", "count": 5}
            ],
            "location": "PALLET TOWN",
            "badges": 0,
            "money": 3000,
            "current_pokemon": "SQUIRTLE"
        }
        
        return self.current_state
    
    def get_state(self):
        """Get the current game state."""
        self.update_game_state()
        return self.current_state
    
    def detect_game_screen(self):
        """Detect what screen we're currently on (battle, overworld, menu, etc.)."""
        # This would use image recognition or memory reading to determine the current screen
        # For now, return a placeholder
        screens = ["overworld", "battle", "menu", "pokemon_list", "item_menu"]
        import random
        return random.choice(screens)

    def is_in_battle(self):
        """Check if the game is currently in a battle."""
        # This would use memory reading to determine if in battle
        # For now, return a placeholder
        return self.detect_game_screen() == "battle"

    def get_game_loop_frequency(self):
        """Return the target frequency for the game loop."""
        return 30  # 30 FPS 