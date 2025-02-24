# Setup and Running Guide

This document provides detailed instructions for setting up and running the Grok Plays Pokémon project.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+**: The project is built on Python
- **Git**: For version control and cloning the repository
- **Pokémon Red ROM**: A legal copy of the Pokémon Red Game Boy ROM (not included)

## System Dependencies

PyBoy (the Game Boy emulator) requires some system dependencies:

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip python3-numpy libsdl2-dev libsdl2-2.0-0
```

### macOS

```bash
brew install sdl2 python
```

### Windows

Install the SDL2 development libraries from [libsdl.org](https://www.libsdl.org/download-2.0.php) or use:

```bash
pip install pysdl2-dll
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/NYTEMODEONLY/grok-plays-pokemon.git
   cd grok-plays-pokemon
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up the ROM directory:
   ```bash
   mkdir -p roms
   ```

5. Copy your legally obtained Pokémon Red ROM to the `roms` directory and rename it to `pokemon_red.gb`:
   ```bash
   cp /path/to/your/pokemon_red.rom roms/pokemon_red.gb
   ```

## Configuration (Optional)

The project uses default settings that work out of the box, but you can customize some aspects:

1. **ROM filename**: If you want to use a differently named ROM file, edit the `ROM_FILE` variable in `app.py`:
   ```python
   ROM_FILE = 'your_rom_name.gb'
   ```

2. **Server host/port**: To change the server host or port, edit the `socketio.run` line in `app.py`:
   ```python
   socketio.run(app, host='0.0.0.0', port=8080, debug=True)
   ```

3. **Screenshot interval**: To adjust how frequently screenshots are captured, modify the `SCREENSHOT_INTERVAL` variable in `app.py`:
   ```python
   SCREENSHOT_INTERVAL = 0.5  # seconds between screenshots
   ```

## Running the Application

1. Start the Flask server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Click the "Start Game" button on the web interface to initialize the emulator and begin gameplay.

## Using the Grok Controller

The project includes a sample controller script (`grok_controller.py`) that demonstrates how Grok AI would control the game:

1. With the server running, open a new terminal window
2. Activate the virtual environment if you created one
3. Run the controller script:
   ```bash
   python grok_controller.py
   ```

This script will:
- Connect to the running server
- Start the game if it's not already running
- Execute a series of actions with commentary
- Simulate playing through the beginning of the game

## Troubleshooting

### Common Issues

#### ROM File Not Found

```
ERROR - ROM file not found: roms/pokemon_red.gb
```

**Solution**: Ensure you have placed your Pokémon Red ROM in the `roms` directory with the correct filename.

#### PyBoy Initialization Error

```
ERROR - Failed to initialize emulator: [SDL Error Message]
```

**Solution**: This usually indicates an issue with SDL2. Make sure you have installed the SDL2 dependencies for your system.

#### Port Already in Use

```
ERROR - Address already in use
```

**Solution**: Another application is using port 5000. Either stop that application or change the port in `app.py`.

#### "No module named 'PyBoy'"

```
ModuleNotFoundError: No module named 'pyboy'
```

**Solution**: Ensure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

### Checking Logs

The application logs information to the console. Look for errors or warnings that might explain any issues you're experiencing.

## Deployment

### Local Network Access

To access the application from other devices on your local network:

1. Make sure the server is running with host `0.0.0.0`:
   ```python
   socketio.run(app, host='0.0.0.0', port=5000, debug=True)
   ```

2. Find your computer's local IP address:
   ```bash
   # On Windows:
   ipconfig
   
   # On macOS/Linux:
   ifconfig
   ```

3. On other devices, navigate to:
   ```
   http://YOUR_LOCAL_IP:5000
   ```

### Internet Deployment

To deploy the application on the internet, consider using:

- **Heroku**: Good for quick deployments
- **AWS/GCP/Azure**: Better for production deployments
- **DigitalOcean**: A simple VPS option

Note that you'll need to adapt the application for production use:

1. Turn off debug mode:
   ```python
   socketio.run(app, host='0.0.0.0', port=5000, debug=False)
   ```

2. Use a production WSGI server (e.g., Gunicorn with eventlet):
   ```bash
   gunicorn --worker-class eventlet -w 1 app:app
   ```

3. Consider using environment variables for configuration:
   ```python
   import os
   
   ROM_FILE = os.environ.get('POKEMON_ROM_FILE', 'pokemon_red.gb')
   ```

## Performance Tips

- **Reduce screenshot quality**: If performance is an issue, you can reduce the quality of screenshots
- **Adjust tick rate**: Modify how many frames the emulator advances per tick
- **Optimize WebSocket traffic**: Reduce the frequency of updates on slow connections

## Next Steps

After setting up the basic application, you might want to:

1. **Implement real memory reading**: Replace the placeholder game state with actual memory reading
2. **Enhance the user interface**: Add more features to the web interface
3. **Improve the AI logic**: Develop more sophisticated gameplay strategies
4. **Add community features**: Allow viewers to interact with the gameplay 