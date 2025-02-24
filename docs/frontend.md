# Frontend Documentation

This document provides information about the frontend components of the Grok Plays Pokémon project, including the HTML, CSS, and JavaScript.

## Overview

The frontend consists of:

- HTML templates (`templates/index.html`)
- CSS styling (`static/css/style.css`)
- JavaScript for dynamic updates (`static/js/app.js`)

The frontend uses WebSockets (Socket.IO) to receive real-time updates from the server.

## Page Structure

The main page is divided into several sections:

1. **Header**: Title and description
2. **Game Screen**: Shows the emulator output
3. **Game Stats**: Displays information about the game state
4. **Commentary**: Shows Grok's commentary on the gameplay

```html
<div class="container">
    <header>
        <h1>Grok Plays Pokémon</h1>
        <!-- ... -->
    </header>
    
    <div class="row">
        <!-- Game Screen Section -->
        <div class="col-md-8">
            <!-- Game screen content -->
        </div>
        
        <!-- Stats and Commentary Section -->
        <div class="col-md-4">
            <!-- Game stats and commentary -->
        </div>
    </div>
    
    <footer>
        <!-- Footer content -->
    </footer>
</div>
```

## Game Screen

The game screen displays the emulator output as an image that is updated in real-time:

```html
<div class="game-screen-container">
    <img id="game-screen" src="{{ url_for('static', filename='img/loading.png') }}" alt="Game Screen" class="img-fluid">
</div>
```

The image is updated via WebSockets when the server sends a new screenshot:

```javascript
socket.on('screenshot_update', (data) => {
    gameScreen.src = `data:image/png;base64,${data.image}`;
});
```

## Game Stats

The game stats section displays information about the current game state, including:

- Pokémon team
- Items
- Location
- Badges
- Money

```html
<div id="game-stats">
    <div class="status-indicator">
        Status: <span id="game-status">Not initialized</span>
    </div>
    <div class="mt-3">
        <h4>Pokémon Team</h4>
        <ul id="pokemon-team" class="list-group">
            <!-- Pokémon team items -->
        </ul>
    </div>
    <!-- Other stats -->
</div>
```

The stats are updated via WebSockets when the server sends a new game state:

```javascript
socket.on('state_update', (data) => {
    updatePokemonTeam(data.pokemon_team);
    updateItemsList(data.items);
    locationEl.textContent = data.location;
    badgesEl.textContent = data.badges;
    moneyEl.textContent = data.money;
});
```

### Pokémon Team Display

Pokémon team members are displayed with their name, level, and HP:

```javascript
function updatePokemonTeam(team) {
    if (!team || team.length === 0) {
        pokemonTeam.innerHTML = '<li class="list-group-item text-center">No Pokémon yet</li>';
        return;
    }

    pokemonTeam.innerHTML = '';
    team.forEach(pokemon => {
        const hpPercent = (pokemon.hp / pokemon.max_hp) * 100;
        const hpColorClass = hpPercent > 50 ? 'bg-success' : hpPercent > 20 ? 'bg-warning' : 'bg-danger';
        
        const pokemonItem = document.createElement('li');
        pokemonItem.className = 'list-group-item';
        pokemonItem.innerHTML = `
            <div class="pokemon-item">
                <div>
                    <span class="pokemon-name">${pokemon.name}</span>
                    <div class="progress" style="height: 5px; width: 100px;">
                        <div class="progress-bar ${hpColorClass}" style="width: ${hpPercent}%" role="progressbar" 
                            aria-valuenow="${pokemon.hp}" aria-valuemin="0" aria-valuemax="${pokemon.max_hp}"></div>
                    </div>
                    <small class="pokemon-hp">${pokemon.hp}/${pokemon.max_hp} HP</small>
                </div>
                <span class="pokemon-level">Lv${pokemon.level}</span>
            </div>
        `;
        pokemonTeam.appendChild(pokemonItem);
    });
}
```

### Items Display

Items are displayed with their name and quantity:

```javascript
function updateItemsList(items) {
    if (!items || items.length === 0) {
        itemsList.innerHTML = '<li class="list-group-item text-center">No items yet</li>';
        return;
    }

    itemsList.innerHTML = '';
    items.forEach(item => {
        const itemElement = document.createElement('li');
        itemElement.className = 'list-group-item';
        itemElement.innerHTML = `
            <span>${item.name}</span>
            <span class="badge bg-secondary">${item.count}</span>
        `;
        itemsList.appendChild(itemElement);
    });
}
```

## Commentary

The commentary section displays Grok's thoughts and explanations about the gameplay:

```html
<div class="card mb-4">
    <div class="card-header">
        <h2>Grok's Commentary</h2>
    </div>
    <div class="card-body">
        <div id="commentary" class="commentary-box">
            <p class="commentary-item">Waiting for Grok to start commenting...</p>
        </div>
    </div>
</div>
```

New commentary is received via WebSockets and added to the commentary box:

```javascript
socket.on('commentary_update', (data) => {
    addCommentary(data.text);
});

function addCommentary(text) {
    const commentaryItem = document.createElement('p');
    commentaryItem.className = 'commentary-item';
    commentaryItem.textContent = text;
    
    commentaryEl.appendChild(commentaryItem);
    commentaryEl.scrollTop = commentaryEl.scrollHeight; // Auto-scroll to bottom
}
```

## Controls

The controls section provides buttons to start and stop the game:

```html
<div id="controls" class="mt-3">
    <button id="start-button" class="btn btn-success me-2">Start Game</button>
    <button id="stop-button" class="btn btn-danger" disabled>Stop Game</button>
</div>
```

These buttons are connected to JavaScript functions that call the API:

```javascript
startButton.addEventListener('click', startGame);
stopButton.addEventListener('click', stopGame);

function startGame() {
    fetch('/api/start_game')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                gameRunning = true;
                updateControlButtons();
                addCommentary('Game started! Waiting for Grok to make the first move...');
            } else {
                addCommentary(`Error starting game: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error starting game:', error);
            addCommentary('Error starting game. Is the ROM file available?');
        });
}

function stopGame() {
    fetch('/api/stop_game')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                gameRunning = false;
                updateControlButtons();
                addCommentary('Game stopped.');
            }
        })
        .catch(error => {
            console.error('Error stopping game:', error);
        });
}
```

## WebSocket Connection

The frontend uses Socket.IO to establish a WebSocket connection with the server:

```javascript
const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
    addCommentary('Connected to Grok Plays Pokémon server!');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addCommentary('Disconnected from server. Trying to reconnect...');
});
```

## CSS Styling

The CSS styling is defined in `static/css/style.css` and includes styles for:

- General page layout
- Game screen container and image
- Game stats display
- Pokémon team and items list
- Commentary box
- Responsive adjustments for different screen sizes

### Highlights:

```css
/* Game Screen Styles */
.game-screen-container {
    background-color: #000;
    padding: 10px;
    border-radius: 5px;
    margin-bottom: 15px;
}

#game-screen {
    max-width: 100%;
    height: auto;
    image-rendering: pixelated; /* Keep pixel art sharp */
    image-rendering: -moz-crisp-edges;
    image-rendering: crisp-edges;
    border: 2px solid #333;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
}

/* Commentary Box Styles */
.commentary-box {
    height: 300px;
    overflow-y: auto;
    background-color: #fff;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
}

.commentary-item {
    margin-bottom: 8px;
    padding: 8px;
    background-color: #f8f9fa;
    border-radius: 5px;
    border-left: 3px solid #007bff;
}
```

## Page Initialization

When the page loads, the JavaScript initializes by checking the current game status:

```javascript
function initializePage() {
    // Check server status
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'running') {
                gameRunning = true;
                updateControlButtons();
                fetchGameState();
                fetchCommentary();
            }
        })
        .catch(error => {
            console.error('Error checking game status:', error);
            addCommentary('Error connecting to server. Please try again later.');
        });
}

// Initialize the page on load
window.addEventListener('load', initializePage);
```

## Future Enhancements

The frontend could be enhanced in several ways:

1. **Game Boy Frame**: Add a Game Boy frame around the game screen for a more authentic look
2. **Dark Mode**: Add a dark mode option for better viewing in low-light conditions
3. **Pokédex Integration**: Add a Pokédex lookup feature for information about encountered Pokémon
4. **Chat System**: Allow visitors to chat and discuss Grok's gameplay
5. **Game Controls**: Add onscreen controls for visitors to suggest moves to Grok
6. **Statistics Dashboard**: Add a more detailed dashboard with game statistics and progress tracking 