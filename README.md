# Grok Plays Pokémon

Watch Grok (xAI's AI) autonomously play through Pokémon Red, Blue, or Yellow! This web application lets viewers watch in real-time as the AI makes decisions, catches Pokémon, battles trainers, and works toward becoming the Pokémon Champion.

## Features

- **Autonomous AI Gameplay**: Grok analyzes the game screen and makes intelligent decisions using the xAI Vision API
- **Real-time Viewer Experience**: Watch the game with live playtime counter, action log, and AI commentary
- **ROM Upload Support**: Upload your own Pokemon Red, Blue, or Yellow ROM files
- **Game State Tracking**: View current Pokémon team, items, location, badges, and more
- **AI Commentary**: Read Grok's thoughts and reasoning as it plays
- **Action Log**: Track every button press and game action in real-time
- **Loop Detection**: Smart detection to prevent the AI from getting stuck

## Requirements

- Python 3.8+
- PyBoy emulator
- Flask web framework
- **xAI API Key** (for autonomous gameplay)
- A legal copy of Pokémon Red/Blue/Yellow ROM (not included)

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/NYTEMODEONLY/grok-plays-pokemon.git
cd grok-plays-pokemon
pip install -r requirements.txt
```

### 2. Configure API Key

Copy the example environment file and add your xAI API key:

```bash
cp .env.example .env
```

Edit `.env` and add your xAI API key:
```
XAI_API_KEY=your_xai_api_key_here
```

Get your API key from: https://console.x.ai/

### 3. Run the Application

```bash
python app.py
```

### 4. Open in Browser

Go to `http://localhost:8000`

### 5. Upload ROM and Play

1. Upload your legally obtained Pokémon ROM file (.gb or .gbc)
2. Click "Start Game"
3. Watch as Grok plays autonomously!

See the [setup documentation](docs/setup.md) for detailed instructions.

## Usage

### Web Interface

The web interface allows you to:
- Upload Pokemon Red, Blue, or Yellow ROM files
- Start and stop the game
- Select which AI controls the player and Pokémon
- Toggle between single AI and dual AI modes
- Watch the game screen, AI commentary, and action log in real-time
- View detailed game state including Pokemon team, items, and location

### Command-line Interface

For advanced users, you can run the AI controller from the command line:

```bash
python multi_ai_controller.py --player grok --pokemon claude --mode dual
```

See the [multi-AI documentation](docs/dual_ai_mode.md) for more details.

## API Endpoints

The application exposes several API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get emulator and game status |
| `/api/state` | GET | Get current game state |
| `/api/gameplay_stats` | GET | Get playtime and action statistics |
| `/api/screenshot` | GET | Get current game screenshot |
| `/api/upload_rom` | POST | Upload a ROM file |
| `/api/start_game` | GET | Start the game |
| `/api/stop_game` | GET | Stop the game |
| `/api/autonomous/start` | POST | Start autonomous AI gameplay |
| `/api/autonomous/stop` | POST | Stop autonomous AI gameplay |

## How It Works

1. **Screen Capture**: The PyBoy emulator captures the game screen
2. **AI Analysis**: The screenshot is sent to xAI's Grok Vision API
3. **Decision Making**: Grok analyzes the screen and decides the next button press
4. **Execution**: The action is executed in the emulator
5. **Commentary**: Grok provides real-time commentary explaining its decisions
6. **Repeat**: The loop continues autonomously

## Documentation

Comprehensive documentation is available in the [docs](docs/) directory:

- [Setup and Installation](docs/setup.md)
- [Game State Tracking](docs/game_state.md)
- [Emulator API](docs/emulator_api.md)
- [Frontend Components](docs/frontend.md)
- [Multi-AI Mode](docs/dual_ai_mode.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Deployment Options

### Option 1: Local/VPS Deployment (Recommended)

For full functionality with the Game Boy emulator, deploy on a server that supports Python native extensions:

```bash
# On your server
git clone https://github.com/NYTEMODEONLY/grok-plays-pokemon.git
cd grok-plays-pokemon
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your XAI_API_KEY
python app.py
```

**Recommended platforms:** DigitalOcean, Linode, AWS EC2, Railway, Render

### Option 2: Vercel (API Only)

The Vercel deployment provides the AI decision-making API only. The emulator must run separately:

1. Deploy to Vercel: `vercel deploy`
2. Set `XAI_API_KEY` in Vercel environment variables
3. The API endpoints will be available for external emulator clients

### Docker Deployment

```bash
# Build and run with Docker
docker build -t grok-plays-pokemon .
docker run -p 8000:8000 -e XAI_API_KEY=your_key grok-plays-pokemon
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XAI_API_KEY` | Yes | Your xAI API key for Grok Vision |
| `FLASK_ENV` | No | Set to `production` for deployment |
| `PORT` | No | Server port (default: 8000) |

## Acknowledgments

- [PyBoy](https://github.com/Baekalfen/PyBoy) for the Game Boy emulator
- [xAI](https://x.ai/) for the Grok Vision API
- Original Pokémon game creators (Game Freak and Nintendo)

## Disclaimer

This project is not affiliated with or endorsed by Nintendo, Game Freak, The Pokémon Company, or xAI. Pokémon is a registered trademark of Nintendo. The creators of this project do not distribute any copyrighted ROM files. 