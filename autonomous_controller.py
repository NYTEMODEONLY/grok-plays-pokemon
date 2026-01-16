#!/usr/bin/env python3
"""
Autonomous Game Controller for Grok Plays Pokemon
This module manages the autonomous gameplay loop using xAI/Grok for decisions.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from collections import deque

try:
    import eventlet
    eventlet.monkey_patch()
    USE_EVENTLET = True
except ImportError:
    USE_EVENTLET = False

from xai_client import get_xai_client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutonomousController:
    """
    Controller that autonomously plays Pokemon using Grok AI.
    """

    def __init__(self, emulator, socketio=None, api_key=None):
        """
        Initialize the autonomous controller.

        Args:
            emulator: PokemonEmulator instance
            socketio: Flask-SocketIO instance for real-time updates
            api_key: Optional xAI API key
        """
        self.emulator = emulator
        self.socketio = socketio
        self.xai_client = get_xai_client(api_key)

        # Game state tracking
        self.is_running = False
        self.is_paused = False
        self.game_thread = None

        # Statistics
        self.start_time = None
        self.total_actions = 0
        self.actions_per_minute = 0
        self.recent_actions = deque(maxlen=50)
        self.action_history = deque(maxlen=1000)

        # Loop detection
        self.position_history = deque(maxlen=20)
        self.loop_detection_threshold = 10
        self.stuck_counter = 0

        # Timing
        self.action_delay = 1.5  # Seconds between actions (to not spam API)
        self.last_action_time = None

        # Screen analysis cache
        self.last_screen_analysis = None
        self.screen_analysis_interval = 5  # Analyze screen every N actions

        logger.info("AutonomousController initialized")

    def start(self):
        """Start the autonomous gameplay loop."""
        if self.is_running:
            logger.warning("Controller already running")
            return False

        if not self.xai_client.is_available():
            logger.error("xAI client not available - cannot start autonomous play")
            self._broadcast_commentary("Error: xAI API key not configured. Please set XAI_API_KEY.")
            return False

        self.is_running = True
        self.is_paused = False
        self.start_time = datetime.now()
        self.total_actions = 0

        if USE_EVENTLET:
            self.game_thread = eventlet.spawn(self._game_loop)
        else:
            self.game_thread = threading.Thread(target=self._game_loop, daemon=True)
            self.game_thread.start()

        logger.info("Autonomous controller started")
        self._broadcast_commentary("Grok is now playing Pokemon autonomously!")
        return True

    def stop(self):
        """Stop the autonomous gameplay loop."""
        self.is_running = False
        if self.game_thread:
            self.game_thread.join(timeout=5)
        logger.info("Autonomous controller stopped")
        self._broadcast_commentary("Grok has stopped playing.")

    def pause(self):
        """Pause the autonomous gameplay."""
        self.is_paused = True
        logger.info("Autonomous controller paused")
        self._broadcast_commentary("Grok is taking a break...")

    def resume(self):
        """Resume the autonomous gameplay."""
        self.is_paused = False
        logger.info("Autonomous controller resumed")
        self._broadcast_commentary("Grok is back to playing!")

    def _game_loop(self):
        """Main autonomous gameplay loop."""
        logger.info("Game loop started")
        action_count = 0

        while self.is_running:
            try:
                sleep_fn = eventlet.sleep if USE_EVENTLET else time.sleep

                if self.is_paused:
                    sleep_fn(0.5)
                    continue

                # Check if emulator is running
                if not self.emulator or not self.emulator.is_running:
                    sleep_fn(1)
                    continue

                # Rate limiting
                if self.last_action_time:
                    elapsed = time.time() - self.last_action_time
                    if elapsed < self.action_delay:
                        sleep_fn(self.action_delay - elapsed)

                # Get current game state
                screenshot = self.emulator.get_screenshot()
                game_state = self.emulator.get_state()

                # Analyze screen periodically
                context = None
                if action_count % self.screen_analysis_interval == 0:
                    self.last_screen_analysis = self.xai_client.analyze_screen(screenshot)
                    context = self.last_screen_analysis.get("suggested_context")

                # Get recent actions for context
                recent = list(self.recent_actions)

                # Check for stuck/loop detection
                if self._detect_stuck(game_state, recent):
                    context = "STUCK DETECTED: Try a different approach. Maybe go in a new direction or press B to cancel."
                    self.stuck_counter += 1
                    if self.stuck_counter > 5:
                        # Force a random different action
                        self._broadcast_commentary("Seems stuck - trying to break out of loop...")
                else:
                    self.stuck_counter = 0

                # Get action from Grok
                result = self.xai_client.get_game_action(
                    screenshot,
                    game_state,
                    recent,
                    context
                )

                action = result["action"]
                commentary = result["commentary"]
                confidence = result["confidence"]

                # Execute the action
                success = self.emulator.execute_action(action)

                if success:
                    self.total_actions += 1
                    action_count += 1
                    self.recent_actions.append(action)
                    self.last_action_time = time.time()

                    # Record in history
                    self.action_history.append({
                        "action": action,
                        "commentary": commentary,
                        "confidence": confidence,
                        "timestamp": time.time(),
                        "game_state": {
                            "location": game_state.get("location"),
                            "badges": game_state.get("badges")
                        }
                    })

                    # Broadcast update
                    self._broadcast_action(action, commentary, confidence)

                    # Log periodically
                    if action_count % 10 == 0:
                        logger.info(f"Action {action_count}: {action} - {commentary[:50]}...")

            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                import traceback
                logger.error(traceback.format_exc())
                sleep_fn = eventlet.sleep if USE_EVENTLET else time.sleep
                sleep_fn(2)  # Wait before retrying

        logger.info("Game loop ended")

    def _detect_stuck(self, game_state, recent_actions):
        """Detect if the AI is stuck in a loop."""
        if len(recent_actions) < self.loop_detection_threshold:
            return False

        # Check for repeated action patterns
        last_n = recent_actions[-self.loop_detection_threshold:]

        # Check for alternating pattern (e.g., left, right, left, right)
        if len(set(last_n)) <= 2:
            return True

        # Check for exact repetition
        half = len(last_n) // 2
        if last_n[:half] == last_n[half:2*half]:
            return True

        # Track position if available
        location = game_state.get("location", "")
        self.position_history.append(location)

        # Check if stuck in same location
        if len(self.position_history) >= 15:
            if len(set(list(self.position_history)[-15:])) == 1:
                return True

        return False

    def _broadcast_action(self, action, commentary, confidence):
        """Broadcast action update to connected clients."""
        if self.socketio:
            confidence_str = f"({int(confidence * 100)}% confident)"
            full_commentary = f"[Grok] {commentary} {confidence_str}"

            self.socketio.emit('commentary_update', {"text": full_commentary})
            self.socketio.emit('action_update', {
                "action": action,
                "commentary": commentary,
                "confidence": confidence,
                "timestamp": time.time()
            })

    def _broadcast_commentary(self, text):
        """Broadcast a commentary message."""
        if self.socketio:
            self.socketio.emit('commentary_update', {"text": f"[System] {text}"})

    def get_stats(self):
        """Get current gameplay statistics."""
        playtime = timedelta(seconds=0)
        if self.start_time:
            playtime = datetime.now() - self.start_time

        # Calculate actions per minute
        if self.start_time and self.total_actions > 0:
            minutes = playtime.total_seconds() / 60
            self.actions_per_minute = self.total_actions / max(minutes, 1)

        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "playtime": str(playtime).split('.')[0],  # Remove microseconds
            "playtime_seconds": int(playtime.total_seconds()),
            "total_actions": self.total_actions,
            "actions_per_minute": round(self.actions_per_minute, 1),
            "recent_actions": list(self.recent_actions)[-10:],
            "last_screen_analysis": self.last_screen_analysis,
            "api_available": self.xai_client.is_available()
        }

    def set_action_delay(self, delay):
        """Set the delay between actions (in seconds)."""
        self.action_delay = max(0.5, min(10.0, delay))
        logger.info(f"Action delay set to {self.action_delay}s")


# Global controller instance
_controller_instance = None


def get_controller(emulator=None, socketio=None, api_key=None):
    """Get or create the autonomous controller singleton."""
    global _controller_instance
    if _controller_instance is None and emulator is not None:
        _controller_instance = AutonomousController(emulator, socketio, api_key)
    return _controller_instance


def reset_controller():
    """Reset the controller instance."""
    global _controller_instance
    if _controller_instance:
        _controller_instance.stop()
    _controller_instance = None
