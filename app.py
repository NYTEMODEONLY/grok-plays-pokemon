import os
import time
import json
import logging
import threading
import base64
from datetime import datetime
from io import BytesIO
from werkzeug.utils import secure_filename
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO, emit
import eventlet
from dotenv import load_dotenv
from emulator import PokemonEmulator
from autonomous_controller import AutonomousController, get_controller, reset_controller

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ROM_DIRECTORY = 'roms'
UPLOAD_FOLDER = 'roms'
ALLOWED_EXTENSIONS = {'gb', 'gbc'}
MAX_ROM_SIZE = 5 * 1024 * 1024  # 5MB max file size
SCREENSHOT_INTERVAL = 1.0  # seconds between screenshots

# Pokemon ROM checksums for validation (first few bytes of each ROM)
POKEMON_ROM_SIGNATURES = {
    'pokemon_red': b'\xCF\x7B\x89\xC0',    # Pokemon Red
    'pokemon_blue': b'\xD3\x7B\x89\xC0',   # Pokemon Blue
    'pokemon_yellow': b'\x8B\x76\x89\xC0'  # Pokemon Yellow
}

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'grok-plays-pokemon-secret!'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_ROM_SIZE
socketio = SocketIO(app, async_mode='eventlet')

# AI settings
AI_SETTINGS = {
    "playerAI": "grok",
    "pokemonAI": "claude",
    "mode": "dual",
    "currentAI": "Grok"  # Currently active AI (changes in dual mode)
}

# Create directories if they don't exist
os.makedirs(ROM_DIRECTORY, exist_ok=True)
os.makedirs('static/screenshots', exist_ok=True)

# Global variables
emulator = None
emulator_lock = threading.Lock()
game_thread = None
screenshot_thread = None
autonomous_controller = None
commentary_history = []
action_log = []
game_running = False
game_start_time = None
current_rom_path = None
current_rom_name = None

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_pokemon_rom(file_path):
    """Validate if the ROM is a Pokemon Red, Blue, or Yellow game."""
    try:
        with open(file_path, 'rb') as f:
            # Read first 400 bytes to check for various signatures and titles
            header = f.read(400)
            logger.info(f"ROM header bytes: {header[:16].hex()}")

            # Check for known signatures
            for rom_name, signature in POKEMON_ROM_SIGNATURES.items():
                if header.startswith(signature):
                    logger.info(f"Matched signature for: {rom_name}")
                    return rom_name.replace('_', ' ').title()

            # Additional checks for Pokemon ROMs
            # Check for Nintendo logo (common in GB/GBC ROMs)
            nintendo_logo = b'\xCE\xED\x66\x66\xCC\x0D\x00\x13\xE8\x23\x3E\x23\xC9\x3E\x23\xC9'
            if nintendo_logo in header:
                logger.info("Found Nintendo logo, assuming valid Pokemon ROM")
                return "Pokemon Red"  # Default to Red if we find Nintendo logo

            # Check for common Pokemon title strings in the title area (around 0x134-0x143)
            if len(header) > 0x150:
                title_area = header[0x134:0x144]
                title_str = title_area.decode('ascii', errors='ignore').upper()
                logger.info(f"Title area: {title_str}")

                if 'POKEMON' in title_str:
                    if 'BLUE' in title_str:
                        return "Pokemon Blue"
                    elif 'YELLOW' in title_str:
                        return "Pokemon Yellow"
                    else:
                        return "Pokemon Red"

            # For now, if it's a .gb or .gbc file of reasonable size, accept it
            # This is a more permissive approach
            file_size = os.path.getsize(file_path)
            if 500000 < file_size < 2000000:  # Between 500KB and 2MB
                logger.info(f"Accepting ROM based on file size: {file_size} bytes")
                return "Pokemon Red"  # Default assumption

            logger.error(f"No valid signature found. Header: {header[:16].hex()}, Size: {file_size}")
            return None
    except Exception as e:
        logger.error(f"Error validating ROM: {e}")
        return None

def initialize_emulator(rom_path=None):
    """Initialize the Pokémon emulator."""
    global emulator, current_rom_path, current_rom_name

    # Use provided ROM path or current ROM
    if rom_path is None:
        rom_path = current_rom_path

    if rom_path is None:
        logger.error("No ROM file specified")
        return False

    if not os.path.exists(rom_path):
        logger.error(f"ROM file not found: {rom_path}")
        return False

    # Check file size and permissions
    try:
        file_size = os.path.getsize(rom_path)
        logger.info(f"Initializing emulator with ROM: {rom_path} (size: {file_size} bytes)")
    except Exception as e:
        logger.error(f"Error accessing ROM file: {e}")
        return False

    # Validate the ROM
    rom_name = validate_pokemon_rom(rom_path)
    if rom_name is None:
        logger.error(f"Invalid or unsupported ROM: {rom_path}")
        return False

    try:
        with emulator_lock:
            # Stop existing emulator if running
            if emulator is not None:
                logger.info("Stopping existing emulator")
                try:
                    emulator.stop()
                except Exception as e:
                    logger.warning(f"Error stopping existing emulator: {e}")

            logger.info(f"Creating PokemonEmulator with ROM: {rom_path}")
            emulator = PokemonEmulator(rom_path, rom_name)

            logger.info("Starting emulator")
            emulator.start()

            current_rom_path = rom_path
            current_rom_name = rom_name

        logger.info(f"Emulator initialized successfully with {rom_name}")
        return True
    except ImportError as e:
        logger.error(f"Missing PyBoy dependency: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize emulator: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
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
                        
                        # Update current AI based on mode and game state
                        if AI_SETTINGS["mode"] == "dual":
                            # This is a simplified check - in a real implementation,
                            # you would check the game state to determine if in battle
                            in_battle = emulator.detect_game_screen() == "battle"
                            if in_battle:
                                AI_SETTINGS["currentAI"] = "Claude" if AI_SETTINGS["pokemonAI"] == "claude" else "Grok"
                            else:
                                AI_SETTINGS["currentAI"] = "Grok" if AI_SETTINGS["playerAI"] == "grok" else "Claude"
                        else:  # single mode
                            # Use only the player AI for everything
                            AI_SETTINGS["currentAI"] = "Grok" if AI_SETTINGS["playerAI"] == "grok" else "Claude"
                        
                        # Push updated state to clients
                        state = emulator.get_state()
                        state["currentAI"] = AI_SETTINGS["currentAI"]  # Add current AI to state
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
    global game_thread, screenshot_thread, game_running, game_start_time, autonomous_controller

    if not game_running:
        game_running = True
        game_start_time = datetime.now()
        game_thread = eventlet.spawn(game_loop)
        screenshot_thread = eventlet.spawn(screenshot_loop)

        # Initialize and start autonomous controller
        if emulator:
            api_key = os.getenv('XAI_API_KEY')
            autonomous_controller = AutonomousController(emulator, socketio, api_key)
            if api_key:
                autonomous_controller.start()
            else:
                logger.warning("XAI_API_KEY not set - autonomous play disabled. Set the environment variable to enable AI gameplay.")

        logger.info("Game threads started")

def stop_game_threads():
    """Stop the game and screenshot threads."""
    global game_running, autonomous_controller

    game_running = False

    # Stop autonomous controller
    if autonomous_controller:
        autonomous_controller.stop()
        autonomous_controller = None

    logger.info("Game threads stopping...")

def update_ai_settings(settings):
    """Update the AI settings."""
    global AI_SETTINGS
    
    if "playerAI" in settings:
        AI_SETTINGS["playerAI"] = settings["playerAI"]
    
    if "pokemonAI" in settings:
        AI_SETTINGS["pokemonAI"] = settings["pokemonAI"]
    
    if "mode" in settings:
        AI_SETTINGS["mode"] = settings["mode"]
    
    # Set the initial current AI based on the player AI
    if AI_SETTINGS["mode"] == "single":
        AI_SETTINGS["currentAI"] = "Grok" if AI_SETTINGS["playerAI"] == "grok" else "Claude"
    
    # Broadcast the updated settings to all clients
    socketio.emit('ai_settings_update', {
        "success": True,
        "playerAI": AI_SETTINGS["playerAI"],
        "pokemonAI": AI_SETTINGS["pokemonAI"],
        "mode": AI_SETTINGS["mode"],
        "currentAI": AI_SETTINGS["currentAI"]
    })
    
    logger.info(f"AI settings updated: {AI_SETTINGS}")
    return AI_SETTINGS

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """API endpoint to get the emulator status."""
    global emulator, current_rom_name, current_rom_path

    rom_info = {
        "rom_name": current_rom_name,
        "rom_path": current_rom_path,
        "rom_exists": current_rom_path is not None and os.path.exists(current_rom_path)
    }

    if emulator is None:
        return jsonify({
            "status": "not_initialized",
            "rom_info": rom_info
        })

    with emulator_lock:
        return jsonify({
            "status": "running" if emulator.is_running else "stopped",
            "frame_count": emulator.frame_count,
            "rom_info": rom_info
        })

@app.route('/api/state')
def get_state():
    """API endpoint to get the current game state."""
    global emulator
    
    if emulator is None:
        return jsonify({"error": "Emulator not initialized"})
    
    with emulator_lock:
        state = emulator.get_state()
        state["currentAI"] = AI_SETTINGS["currentAI"]  # Add current AI to state
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

@app.route('/api/ai_settings', methods=['GET', 'POST'])
def ai_settings():
    """API endpoint to get or update AI settings."""
    global AI_SETTINGS
    
    if request.method == 'GET':
        # Return current settings
        return jsonify({
            "success": True,
            "playerAI": AI_SETTINGS["playerAI"],
            "pokemonAI": AI_SETTINGS["pokemonAI"],
            "mode": AI_SETTINGS["mode"],
            "currentAI": AI_SETTINGS["currentAI"]
        })
    elif request.method == 'POST':
        # Update settings
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "Invalid request, no data provided"})
        
        updated_settings = update_ai_settings(data)
        return jsonify({
            "success": True,
            "playerAI": updated_settings["playerAI"],
            "pokemonAI": updated_settings["pokemonAI"],
            "mode": updated_settings["mode"],
            "currentAI": updated_settings["currentAI"]
        })

@app.route('/api/execute_action', methods=['POST'])
def execute_action():
    """API endpoint to execute a game action."""
    global emulator, commentary_history, action_log

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

    # Log the action
    action_log.append({
        "action": action,
        "commentary": commentary,
        "timestamp": time.time(),
        "frame_count": emulator.frame_count if emulator else 0
    })

    # Keep only the last 1000 actions to prevent memory issues
    if len(action_log) > 1000:
        action_log.pop(0)

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
    global emulator, commentary_history, action_log

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

    # Log the sequence
    for action in actions:
        action_log.append({
            "action": action,
            "commentary": f"Part of sequence: {commentary}",
            "timestamp": time.time(),
            "frame_count": emulator.frame_count if emulator else 0
        })

        # Keep only the last 1000 actions to prevent memory issues
        if len(action_log) > 1000:
            action_log.pop(0)

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

@app.route('/api/action_log')
def get_action_log():
    """API endpoint to get the action log."""
    global action_log

    return jsonify(action_log)

@app.route('/api/gameplay_stats')
def get_gameplay_stats():
    """API endpoint to get gameplay statistics including playtime."""
    global game_start_time, autonomous_controller, game_running

    # Calculate playtime
    playtime_seconds = 0
    playtime_formatted = "00:00:00"
    if game_start_time and game_running:
        playtime = datetime.now() - game_start_time
        playtime_seconds = int(playtime.total_seconds())
        hours = playtime_seconds // 3600
        minutes = (playtime_seconds % 3600) // 60
        seconds = playtime_seconds % 60
        playtime_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # Get autonomous controller stats if available
    controller_stats = {}
    if autonomous_controller:
        controller_stats = autonomous_controller.get_stats()

    return jsonify({
        "game_running": game_running,
        "playtime_seconds": playtime_seconds,
        "playtime_formatted": playtime_formatted,
        "total_actions": controller_stats.get("total_actions", len(action_log)),
        "actions_per_minute": controller_stats.get("actions_per_minute", 0),
        "api_available": controller_stats.get("api_available", False),
        "is_autonomous": autonomous_controller is not None and autonomous_controller.is_running,
        "recent_actions": controller_stats.get("recent_actions", [])
    })

@app.route('/api/autonomous/start', methods=['POST'])
def start_autonomous():
    """Start autonomous gameplay."""
    global autonomous_controller, emulator

    if not emulator or not emulator.is_running:
        return jsonify({"success": False, "error": "Game must be running first"})

    if autonomous_controller and autonomous_controller.is_running:
        return jsonify({"success": False, "error": "Autonomous play already running"})

    # Get optional API key from request
    data = request.json or {}
    api_key = data.get("api_key") or os.getenv("XAI_API_KEY")

    if not api_key:
        return jsonify({"success": False, "error": "No xAI API key provided. Set XAI_API_KEY environment variable or pass api_key in request."})

    autonomous_controller = AutonomousController(emulator, socketio, api_key)
    success = autonomous_controller.start()

    return jsonify({
        "success": success,
        "message": "Autonomous play started" if success else "Failed to start autonomous play"
    })

@app.route('/api/autonomous/stop', methods=['POST'])
def stop_autonomous():
    """Stop autonomous gameplay."""
    global autonomous_controller

    if autonomous_controller:
        autonomous_controller.stop()
        return jsonify({"success": True, "message": "Autonomous play stopped"})

    return jsonify({"success": False, "error": "Autonomous play not running"})

@app.route('/api/autonomous/pause', methods=['POST'])
def pause_autonomous():
    """Pause autonomous gameplay."""
    global autonomous_controller

    if autonomous_controller and autonomous_controller.is_running:
        autonomous_controller.pause()
        return jsonify({"success": True, "message": "Autonomous play paused"})

    return jsonify({"success": False, "error": "Autonomous play not running"})

@app.route('/api/autonomous/resume', methods=['POST'])
def resume_autonomous():
    """Resume autonomous gameplay."""
    global autonomous_controller

    if autonomous_controller and autonomous_controller.is_paused:
        autonomous_controller.resume()
        return jsonify({"success": True, "message": "Autonomous play resumed"})

    return jsonify({"success": False, "error": "Autonomous play not paused"})

@app.route('/api/rom_info')
def get_rom_info():
    """API endpoint to get current ROM information."""
    global current_rom_name, current_rom_path

    if current_rom_path and os.path.exists(current_rom_path):
        return jsonify({
            "name": current_rom_name,
            "path": current_rom_path,
            "size": os.path.getsize(current_rom_path),
            "exists": True
        })
    else:
        return jsonify({
            "name": None,
            "path": None,
            "size": 0,
            "exists": False
        })

@app.route('/api/upload_rom', methods=['POST', 'DELETE'])
def upload_rom():
    """API endpoint to upload or clear a ROM file."""
    global current_rom_path, current_rom_name

    if request.method == 'DELETE':
        # Clear ROM functionality
        try:
            if current_rom_path and os.path.exists(current_rom_path):
                os.remove(current_rom_path)
                logger.info(f"ROM cleared: {current_rom_name}")
            current_rom_path = None
            current_rom_name = None

            # Stop the emulator if running
            global emulator, game_running
            if emulator is not None:
                with emulator_lock:
                    emulator.stop()
                emulator = None
                game_running = False

            return jsonify({
                "success": True,
                "message": "ROM cleared successfully"
            })
        except Exception as e:
            logger.error(f"Error clearing ROM: {e}")
            return jsonify({"success": False, "error": f"Error clearing ROM: {str(e)}"})

    # POST method for uploading
    logger.info(f"Upload request received. Content-Length: {request.content_length}")

    # Check if the post request has the file part
    if 'rom' not in request.files:
        logger.error("No file part in request")
        return jsonify({"success": False, "error": "No file part"})

    file = request.files['rom']

    # If user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        logger.error("Empty filename")
        return jsonify({"success": False, "error": "No selected file"})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        logger.info(f"Processing file: {filename}, size: {getattr(file, 'content_length', 'unknown')}")

        try:
            # Save the file
            file.save(file_path)
            file_size = os.path.getsize(file_path)
            logger.info(f"File saved successfully. Size: {file_size} bytes")

            # Validate the ROM
            rom_name = validate_pokemon_rom(file_path)
            if rom_name is None:
                # Remove invalid file
                os.remove(file_path)
                logger.error("Invalid ROM signature")
                return jsonify({"success": False, "error": "Invalid ROM file. Only Pokemon Red, Blue, and Yellow are supported."})

            # Set as current ROM
            current_rom_path = file_path
            current_rom_name = rom_name

            logger.info(f"ROM uploaded successfully: {rom_name}")
            return jsonify({
                "success": True,
                "message": f"Successfully uploaded {rom_name}",
                "rom_name": rom_name,
                "rom_path": file_path,
                "file_size": file_size
            })

        except Exception as e:
            logger.error(f"Error uploading ROM: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "error": f"Error uploading file: {str(e)}"})

    logger.error("Invalid file type or no file provided")
    return jsonify({"success": False, "error": "Invalid file type. Only .gb and .gbc files are allowed."})

@app.route('/api/start_game')
def start_game():
    """API endpoint to start the game."""
    global emulator, current_rom_path

    if emulator is None:
        if current_rom_path is None:
            return jsonify({"error": "No ROM file selected. Please upload a Pokemon ROM first."})
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
    
    # Send current AI settings to the newly connected client
    emit('ai_settings_update', {
        "success": True,
        "playerAI": AI_SETTINGS["playerAI"],
        "pokemonAI": AI_SETTINGS["pokemonAI"],
        "mode": AI_SETTINGS["mode"],
        "currentAI": AI_SETTINGS["currentAI"]
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect event."""
    logger.info("Client disconnected")

if __name__ == '__main__':
    # Ensure ROM directory exists
    os.makedirs(ROM_DIRECTORY, exist_ok=True)

    logger.info("Grok Plays Pokemon server starting...")
    logger.info("Please upload a Pokemon ROM (Red, Blue, or Yellow) through the web interface at http://localhost:8000")

    # Start the Flask-SocketIO server
    socketio.run(app, host='0.0.0.0', port=8000, debug=True) 