# Emulator API Documentation

This document provides detailed information about the emulator interface and API endpoints available in the Grok Plays Pokémon project.

## PokemonEmulator Class

The `PokemonEmulator` class in `emulator.py` is the main interface to the PyBoy emulator. It provides methods to control the game, read the game state, and capture screenshots.

### Initialization

```python
emulator = PokemonEmulator(rom_path)
```

Parameters:
- `rom_path`: Path to the Pokémon Red ROM file

### Main Methods

#### Game Control

- `start()`: Start the emulator
- `stop()`: Stop the emulator
- `tick(frames=1)`: Advance the emulator by a number of frames
- `run_for_seconds(seconds)`: Run the emulator for a specified number of seconds
- `execute_action(action)`: Execute a single game action (button press)
- `execute_sequence(actions, delay=10)`: Execute a sequence of actions with delays

#### Game State

- `get_state()`: Get the current game state
- `update_game_state()`: Update the game state information
- `is_in_battle()`: Check if the game is currently in a battle
- `detect_game_screen()`: Detect what screen we're currently on

#### Visuals

- `get_screenshot()`: Get the current screenshot of the game
- `get_screen_ndarray()`: Get the current screen as a numpy array
- `save_screenshot(path)`: Save the current screenshot to a file

### Game Actions

The following actions can be used with `execute_action()` and `execute_sequence()`:

- `a`: Press the A button
- `b`: Press the B button
- `start`: Press the Start button
- `select`: Press the Select button
- `up`: Press the Up direction
- `down`: Press the Down direction
- `left`: Press the Left direction
- `right`: Press the Right direction

### Game State Structure

The game state object returned by `get_state()` has the following structure:

```json
{
  "pokemon_team": [
    {
      "name": "SQUIRTLE",
      "level": 5,
      "hp": 20,
      "max_hp": 20
    }
  ],
  "items": [
    {
      "name": "Potion",
      "count": 1
    },
    {
      "name": "Poké Ball",
      "count": 5
    }
  ],
  "location": "PALLET TOWN",
  "badges": 0,
  "money": 3000,
  "current_pokemon": "SQUIRTLE"
}
```

## Web API Endpoints

The Flask application in `app.py` provides the following API endpoints:

### GET Endpoints

- `GET /api/status`: Get the current emulator status
  - Response: `{"status": "running", "frame_count": 1234}`

- `GET /api/state`: Get the current game state
  - Response: Game state object (see above)

- `GET /api/screenshot`: Get the current game screen image
  - Response: PNG image

- `GET /api/commentary`: Get the commentary history
  - Response: Array of commentary objects with text and timestamp

- `GET /api/start_game`: Start the game emulator
  - Response: `{"success": true, "status": "started"}`

- `GET /api/stop_game`: Stop the game emulator
  - Response: `{"success": true, "status": "stopped"}`

### POST Endpoints

- `POST /api/execute_action`: Execute a single game action
  - Request: `{"action": "a", "commentary": "Optional commentary"}`
  - Response: `{"success": true, "action": "a"}`

- `POST /api/execute_sequence`: Execute a sequence of game actions
  - Request: `{"actions": ["up", "up", "a"], "commentary": "Optional commentary"}`
  - Response: `{"success": true, "results": [true, true, true], "actions": ["up", "up", "a"]}`

## WebSocket Events

The application uses Socket.IO for real-time updates:

### Emitted Events

- `screenshot_update`: Emitted when a new screenshot is available
  - Data: `{"image": "base64-encoded-png-data"}`

- `state_update`: Emitted when the game state is updated
  - Data: Game state object (see above)

- `commentary_update`: Emitted when new commentary is added
  - Data: `{"text": "Commentary text"}`

### Received Events

- `connect`: Received when a client connects
- `disconnect`: Received when a client disconnects

## Example Usage

### Executing a Game Action

```python
import requests

response = requests.post(
    "http://localhost:5000/api/execute_action",
    json={
        "action": "a",
        "commentary": "Selecting Squirtle as my starter!"
    }
)
print(response.json())
```

### Executing a Sequence of Actions

```python
import requests

response = requests.post(
    "http://localhost:5000/api/execute_sequence",
    json={
        "actions": ["up", "up", "right", "a"],
        "commentary": "Moving to and talking to Professor Oak"
    }
)
print(response.json())
```

### Getting the Game State

```python
import requests

response = requests.get("http://localhost:5000/api/state")
game_state = response.json()
print(f"Current location: {game_state['location']}")
print(f"Pokémon team: {game_state['pokemon_team']}")
``` 