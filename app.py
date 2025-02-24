import os
import time
import json
import logging
import threading
import base64
from io import BytesIO
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import eventlet
from emulator import PokemonEmulator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'grok-plays-pokemon-secret!'
socketio = SocketIO(app, async_mode='eventlet')

# Configuration
ROM_DIRECTORY = 'roms'
ROM_FILE = 'pokemon_red.gb'  # User must provide this
SCREENSHOT_INTERVAL = 1.0  # seconds between screenshots

# Create directories if they don't exist
os.makedirs(ROM_DIRECTORY, exist_ok=True)
os.makedirs('static/screenshots', exist_ok=True)

# Global variables
emulator = None
emulator_lock = threading.Lock()
game_thread = None
screenshot_thread = None
commentary_history = []
game_running = False

def initialize_emulator():
    """Initialize the Pokémon emulator."""
    global emulator
    
    rom_path = os.path.join(ROM_DIRECTORY, ROM_FILE)
    if not os.path.exists(rom_path):
        logger.error(f"ROM file not found: {rom_path}")
        return False
    
    try:
        with emulator_lock:
            emulator = PokemonEmulator(rom_path)
            emulator.start()
        logger.info("Emulator initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize emulator: {e}")
        return False

def game_loop():
    """Main game loop that runs in a separate thread."""
    global game_running
    
    logger.info("Starting game loop")
    game_running = True
    
    try:
        while game_running:
            with emulator_lock:
                if emulator and emulator.is_running:
                    # Advance the game by a few frames
                    emulator.tick(2)
                    
                    # Check if we need to update game state
                    if emulator.frame_count % 30 == 0:  # Every 30 frames (roughly 0.5 seconds)
                        emulator.update_game_state()
                        
                        # Push updated state to clients
                        state = emulator.get_state()
                        socketio.emit('state_update', state)
            
            # Sleep to control game loop frequency
            eventlet.sleep(1/30)  # 30 FPS target
    except Exception as e:
        logger.error(f"Error in game loop: {e}")
    finally:
        logger.info("Game loop stopped")
        game_running = False

def screenshot_loop():
    """Loop that captures and broadcasts screenshots."""
    logger.info("Starting screenshot loop")
    
    try:
        while game_running:
            with emulator_lock:
                if emulator and emulator.is_running:
                    # Capture screenshot
                    screenshot = emulator.get_screenshot()
                    
                    # Convert to base64 for web display
                    buffered = BytesIO()
                    screenshot.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                    
                    # Emit to clients
                    socketio.emit('screenshot_update', {'image': img_str})
            
            # Sleep to control screenshot frequency
            eventlet.sleep(SCREENSHOT_INTERVAL)
    except Exception as e:
        logger.error(f"Error in screenshot loop: {e}")
    finally:
        logger.info("Screenshot loop stopped")

def start_game_threads():
    """Start the game and screenshot threads."""
    global game_thread, screenshot_thread, game_running
    
    if not game_running:
        game_running = True
        game_thread = eventlet.spawn(game_loop)
        screenshot_thread = eventlet.spawn(screenshot_loop)
        logger.info("Game threads started")

def stop_game_threads():
    """Stop the game and screenshot threads."""
    global game_running
    
    game_running = False
    logger.info("Game threads stopping...")

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """API endpoint to get the emulator status."""
    global emulator
    
    if emulator is None:
        return jsonify({"status": "not_initialized"})
    
    with emulator_lock:
        return jsonify({
            "status": "running" if emulator.is_running else "stopped",
            "frame_count": emulator.frame_count
        })

@app.route('/api/state')
def get_state():
    """API endpoint to get the current game state."""
    global emulator
    
    if emulator is None:
        return jsonify({"error": "Emulator not initialized"})
    
    with emulator_lock:
        state = emulator.get_state()
        return jsonify(state)

@app.route('/api/screenshot')
def get_screenshot():
    """API endpoint to get the current screenshot."""
    global emulator
    
    if emulator is None:
        return jsonify({"error": "Emulator not initialized"})
    
    with emulator_lock:
        screenshot = emulator.get_screenshot()
        
        # Convert to bytes for HTTP response
        img_io = BytesIO()
        screenshot.save(img_io, 'PNG')
        img_io.seek(0)
        
        return Response(img_io.getvalue(), mimetype='image/png')

@app.route('/api/execute_action', methods=['POST'])
def execute_action():
    """API endpoint to execute a game action."""
    global emulator, commentary_history
    
    if emulator is None:
        return jsonify({"error": "Emulator not initialized"})
    
    data = request.json
    if not data or 'action' not in data:
        return jsonify({"error": "Invalid request, 'action' field required"})
    
    action = data['action']
    commentary = data.get('commentary', '')
    
    # Add commentary to history
    if commentary:
        commentary_history.append({
            "text": commentary,
            "timestamp": time.time()
        })
        socketio.emit('commentary_update', {"text": commentary})
    
    # Execute the action in the emulator
    with emulator_lock:
        success = emulator.execute_action(action)
        
        if success:
            logger.info(f"Action executed: {action}")
            return jsonify({"success": True, "action": action})
        else:
            logger.warning(f"Failed to execute action: {action}")
            return jsonify({"success": False, "error": f"Invalid action: {action}"})

@app.route('/api/execute_sequence', methods=['POST'])
def execute_sequence():
    """API endpoint to execute a sequence of game actions."""
    global emulator
    
    if emulator is None:
        return jsonify({"error": "Emulator not initialized"})
    
    data = request.json
    if not data or 'actions' not in data:
        return jsonify({"error": "Invalid request, 'actions' field required"})
    
    actions = data['actions']
    commentary = data.get('commentary', '')
    
    # Add commentary to history
    if commentary:
        commentary_history.append({
            "text": commentary,
            "timestamp": time.time()
        })
        socketio.emit('commentary_update', {"text": commentary})
    
    # Execute the action sequence in the emulator
    with emulator_lock:
        results = emulator.execute_sequence(actions)
        
        return jsonify({
            "success": all(results),
            "results": results,
            "actions": actions
        })

@app.route('/api/commentary')
def get_commentary():
    """API endpoint to get the commentary history."""
    global commentary_history
    
    return jsonify(commentary_history)

@app.route('/api/start_game')
def start_game():
    """API endpoint to start the game."""
    global emulator
    
    if emulator is None:
        if not initialize_emulator():
            return jsonify({"error": "Failed to initialize emulator"})
    
    with emulator_lock:
        emulator.start()
    
    start_game_threads()
    return jsonify({"success": True, "status": "started"})

@app.route('/api/stop_game')
def stop_game():
    """API endpoint to stop the game."""
    global emulator
    
    stop_game_threads()
    
    if emulator is not None:
        with emulator_lock:
            emulator.stop()
    
    return jsonify({"success": True, "status": "stopped"})

@socketio.on('connect')
def handle_connect():
    """Handle client connect event."""
    logger.info("Client connected")
    emit('commentary_update', {"text": "Connected to Grok Plays Pokémon!"})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect event."""
    logger.info("Client disconnected")

if __name__ == '__main__':
    # Check if ROM file exists
    rom_path = os.path.join(ROM_DIRECTORY, ROM_FILE)
    if not os.path.exists(rom_path):
        logger.warning(f"ROM file not found: {rom_path}")
        logger.warning("Please place your Pokemon Red ROM in the 'roms' directory.")
    
    # Start the Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 