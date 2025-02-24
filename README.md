# Grok Plays Pokémon

A web-based experience where Grok (an AI) plays Pokémon Red autonomously via an API-controlled emulator, with visitors watching the gameplay live.

## Overview

This project consists of:
- PyBoy emulator running Pokémon Red
- Python backend that interfaces with the emulator
- Flask web server for API and streaming
- Web frontend for visitors to watch the game

## Requirements

- Python 3.8+
- PyBoy dependencies (see PyBoy documentation)
- A legal Pokémon Red ROM file (not included)

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Place your Pokémon Red ROM in the `roms` directory
4. Run the server:
   ```
   python app.py
   ```
5. Open your browser to `http://localhost:5000`

## Project Structure

- `app.py`: Main Flask application
- `emulator.py`: PyBoy integration and game state management
- `templates/`: Frontend HTML templates
- `static/`: CSS, JavaScript, and assets
- `roms/`: Directory for the Pokémon ROM (not included)

## How It Works

1. The PyBoy emulator runs the game in the backend
2. Grok AI provides decisions on gameplay via API calls
3. The emulator executes those actions
4. Game screens and state are streamed to the web frontend
5. Visitors can watch the gameplay and Grok's commentary in real-time 