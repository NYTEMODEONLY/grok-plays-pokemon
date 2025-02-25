# Grok Plays Pokémon

A web application for watching AI play through Pokémon Red/Blue, featuring multiple AI players and dual-AI gameplay modes.

## Features

- **Web-based Interface**: Watch the AI play in real-time through a web browser
- **Game State Tracking**: View current Pokémon team, items, location, and more
- **AI Commentary**: Read the AI's thoughts and reasoning as it plays
- **Multiple AIs**: Choose between Grok and Claude 3.7 Sonnet as your AI players
- **Dual-AI Mode**: Have one AI control the player and another control the Pokémon during battles

## Requirements

- Python 3.8+
- PyBoy emulator
- Flask web framework
- A legal copy of Pokémon Red/Blue ROM (not included)

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Place your legally obtained Pokémon ROM in the `roms` directory as `pokemon_red.gb`
4. Run the application: `python app.py`
5. Open your browser and go to `http://localhost:5000`

See the [setup documentation](docs/setup.md) for detailed instructions.

## Usage

### Web Interface

The web interface allows you to:
- Start and stop the game
- Select which AI controls the player and Pokémon
- Toggle between single AI and dual AI modes
- Watch the game screen and read AI commentary in real-time

### Command-line Interface

For advanced users, you can run the AI controller from the command line:

```bash
python multi_ai_controller.py --player grok --pokemon claude --mode dual
```

See the [multi-AI documentation](docs/dual_ai_mode.md) for more details.

## Documentation

Comprehensive documentation is available in the [docs](docs/) directory:

- [Setup and Installation](docs/setup.md)
- [Game State Tracking](docs/game_state.md)
- [Emulator API](docs/emulator_api.md)
- [Frontend Components](docs/frontend.md)
- [Multi-AI Mode](docs/dual_ai_mode.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [PyBoy](https://github.com/Baekalfen/PyBoy) for the Game Boy emulator
- Original Pokémon game creators (Game Freak and Nintendo)

## Disclaimer

This project is not affiliated with or endorsed by Nintendo, Game Freak, or The Pokémon Company. Pokémon is a registered trademark of Nintendo. The creators of this project do not distribute any copyrighted ROM files. 