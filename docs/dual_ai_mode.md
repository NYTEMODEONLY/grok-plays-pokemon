# Dual AI Mode

This document explains the Multi-AI functionality in Grok Plays Pokémon, which allows you to use different AI models to control different aspects of gameplay.

## Overview

Grok Plays Pokémon now supports two AI models:
1. **Grok** - The original AI player
2. **Claude 3.7 Sonnet** - A new AI model with different playing strategies

You can use these AIs in two different modes:

### Single AI Mode

In Single AI Mode, one AI controls everything - both player movement during exploration and Pokémon actions during battles. This is similar to the original implementation, but now you can choose which AI you want to use.

- Select the AI you want in the **Player AI** dropdown
- Set mode to **Single AI**
- The Pokémon AI setting is ignored in this mode

### Dual AI Mode

In Dual AI Mode, two different AIs can control different aspects of the game:

- **Player AI** controls character movement, world exploration, and NPC interactions
- **Pokémon AI** takes over during battles to control Pokémon move selection and battle strategies

This mode is great for seeing how different AIs approach different aspects of gameplay. For example, Grok might excel at exploration while Claude might have better battle strategies, or vice versa!

## How to Use

### Via Web Interface

1. Open the web interface at `http://localhost:5000`
2. In the **AI Selection** section:
   - Choose your preferred **Player AI** (Grok or Claude)
   - Choose your preferred **Pokémon AI** (Grok or Claude)
   - Select your mode (**Single AI** or **Dual AI**)
3. Click **Apply AI Settings**
4. Start the game with the **Start Game** button

### Via Command Line

You can also control the AIs via the command line using `multi_ai_controller.py`:

```bash
# Run with Grok as player AI and Claude as Pokémon AI in dual mode (default)
python multi_ai_controller.py

# Run with Claude for everything (single mode)
python multi_ai_controller.py --player claude --mode single

# Run with Grok for player movement and Grok for battles in dual mode
python multi_ai_controller.py --player grok --pokemon grok --mode dual

# Run for a specific number of steps with custom delay
python multi_ai_controller.py --steps 200 --delay 0.5
```

## AI Personalities and Strategies

The two AIs have different gameplay styles:

### Grok
- More explorative and risk-taking
- Prefers direct, aggressive battle strategies
- Favors Squirtle as a starter Pokémon

### Claude 3.7 Sonnet
- More methodical and strategic
- Considers type advantages during battles
- More likely to use items strategically
- Favors Bulbasaur as a starter Pokémon

## Technical Implementation

The multi-AI functionality is implemented through:
- An AI controller framework (`ai_controller.py`)
- A command-line interface (`multi_ai_controller.py`) 
- Backend API endpoints for AI settings
- Frontend UI for AI selection

The system detects whether the game is in battle mode and automatically switches between the appropriate AIs in dual mode.

## Feedback and Improvements

This is an experimental feature! If you notice interesting differences between the AIs or have suggestions for improvements, please open an issue on the GitHub repository. 