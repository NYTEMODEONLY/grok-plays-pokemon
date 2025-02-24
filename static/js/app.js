// Connect to Socket.IO server
const socket = io();

// DOM Elements
const gameScreen = document.getElementById('game-screen');
const gameStatus = document.getElementById('game-status');
const pokemonTeam = document.getElementById('pokemon-team');
const itemsList = document.getElementById('items-list');
const locationEl = document.getElementById('location');
const badgesEl = document.getElementById('badges');
const moneyEl = document.getElementById('money');
const commentaryEl = document.getElementById('commentary');
const startButton = document.getElementById('start-button');
const stopButton = document.getElementById('stop-button');

// Game state
let gameRunning = false;

// Initialize the page
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

// Update the Pokemon team list
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

// Update the items list
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

// Add a commentary message
function addCommentary(text) {
    const commentaryItem = document.createElement('p');
    commentaryItem.className = 'commentary-item';
    commentaryItem.textContent = text;
    
    commentaryEl.appendChild(commentaryItem);
    commentaryEl.scrollTop = commentaryEl.scrollHeight; // Auto-scroll to bottom
}

// Fetch game state from API
function fetchGameState() {
    if (!gameRunning) return;
    
    fetch('/api/state')
        .then(response => response.json())
        .then(data => {
            updatePokemonTeam(data.pokemon_team);
            updateItemsList(data.items);
            locationEl.textContent = data.location;
            badgesEl.textContent = data.badges;
            moneyEl.textContent = data.money;
        })
        .catch(error => {
            console.error('Error fetching game state:', error);
        });
}

// Fetch commentary history
function fetchCommentary() {
    fetch('/api/commentary')
        .then(response => response.json())
        .then(data => {
            commentaryEl.innerHTML = '';
            if (data.length === 0) {
                addCommentary('Waiting for Grok to start commenting...');
            } else {
                data.forEach(comment => {
                    addCommentary(comment.text);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching commentary:', error);
        });
}

// Update control buttons based on game state
function updateControlButtons() {
    if (gameRunning) {
        startButton.disabled = true;
        stopButton.disabled = false;
        gameStatus.textContent = 'Running';
        gameStatus.style.color = '#28a745';
    } else {
        startButton.disabled = false;
        stopButton.disabled = true;
        gameStatus.textContent = 'Stopped';
        gameStatus.style.color = '#dc3545';
    }
}

// Start the game
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

// Stop the game
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

// Socket.IO event listeners
socket.on('connect', () => {
    console.log('Connected to server');
    addCommentary('Connected to Grok Plays Pokémon server!');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addCommentary('Disconnected from server. Trying to reconnect...');
});

socket.on('screenshot_update', (data) => {
    gameScreen.src = `data:image/png;base64,${data.image}`;
});

socket.on('state_update', (data) => {
    updatePokemonTeam(data.pokemon_team);
    updateItemsList(data.items);
    locationEl.textContent = data.location;
    badgesEl.textContent = data.badges;
    moneyEl.textContent = data.money;
});

socket.on('commentary_update', (data) => {
    addCommentary(data.text);
});

// Event listeners
startButton.addEventListener('click', startGame);
stopButton.addEventListener('click', stopGame);

// Initialize the page on load
window.addEventListener('load', initializePage); 