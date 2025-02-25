// Connect to Socket.IO server
const socket = io();

// DOM Elements
const gameScreen = document.getElementById('game-screen');
const gameStatus = document.getElementById('game-status');
const activeAIName = document.getElementById('active-ai-name');
const pokemonTeam = document.getElementById('pokemon-team');
const itemsList = document.getElementById('items-list');
const locationEl = document.getElementById('location');
const badgesEl = document.getElementById('badges');
const moneyEl = document.getElementById('money');
const commentaryEl = document.getElementById('commentary');
const startButton = document.getElementById('start-button');
const stopButton = document.getElementById('stop-button');
const applyAISettingsButton = document.getElementById('apply-ai-settings');
const playerAISelect = document.getElementById('player-ai');
const pokemonAISelect = document.getElementById('pokemon-ai');
const aiModeSelect = document.getElementById('ai-mode');

// Game state
let gameRunning = false;
let currentAISettings = {
    playerAI: 'grok',
    pokemonAI: 'claude',
    mode: 'dual'
};

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
                fetchAISettings();
            }
        })
        .catch(error => {
            console.error('Error checking game status:', error);
            addCommentary('Error connecting to server. Please try again later.');
        });
    
    // Load initial AI settings from localStorage if available
    loadAISettings();
}

// Load saved AI settings from localStorage
function loadAISettings() {
    const savedSettings = localStorage.getItem('aiSettings');
    if (savedSettings) {
        try {
            const settings = JSON.parse(savedSettings);
            playerAISelect.value = settings.playerAI || 'grok';
            pokemonAISelect.value = settings.pokemonAI || 'claude';
            aiModeSelect.value = settings.mode || 'dual';
            currentAISettings = settings;
        } catch (e) {
            console.error('Error loading AI settings:', e);
        }
    }
}

// Save AI settings to localStorage
function saveAISettings() {
    localStorage.setItem('aiSettings', JSON.stringify(currentAISettings));
}

// Fetch current AI settings from server
function fetchAISettings() {
    fetch('/api/ai_settings')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                playerAISelect.value = data.playerAI;
                pokemonAISelect.value = data.pokemonAI;
                aiModeSelect.value = data.mode;
                currentAISettings = {
                    playerAI: data.playerAI,
                    pokemonAI: data.pokemonAI,
                    mode: data.mode
                };
                saveAISettings();
                updateActiveAIDisplay(data.currentAI);
            }
        })
        .catch(error => {
            console.error('Error fetching AI settings:', error);
        });
}

// Update the UI based on AI mode
function updateAIModeDisplay() {
    // Visually indicate mode in the UI
    const aiControlsSection = document.getElementById('ai-controls');
    
    if (aiModeSelect.value === 'single') {
        // Add visual indication that we're in single mode
        aiControlsSection.classList.add('single-mode');
        aiControlsSection.classList.remove('dual-mode');
        
        // Grey out the Pokémon AI selector since it's not used in single mode
        document.getElementById('pokemon-ai').parentElement.classList.add('disabled-setting');
        document.querySelector('[for="pokemon-ai"]').classList.add('text-muted');
    } else {
        // Add visual indication that we're in dual mode
        aiControlsSection.classList.add('dual-mode');
        aiControlsSection.classList.remove('single-mode');
        
        // Ensure Pokémon AI selector is fully enabled
        document.getElementById('pokemon-ai').parentElement.classList.remove('disabled-setting');
        document.querySelector('[for="pokemon-ai"]').classList.remove('text-muted');
    }
}

// Apply AI settings to the server
function applyAISettings() {
    const settings = {
        playerAI: playerAISelect.value,
        pokemonAI: pokemonAISelect.value,
        mode: aiModeSelect.value
    };
    
    // Update the UI first
    updateAIModeDisplay();
    
    fetch('/api/ai_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Generate appropriate message based on mode
                let message = '';
                if (settings.mode === 'single') {
                    const aiName = settings.playerAI === 'grok' ? 'Grok' : 'Claude 3.7 Sonnet';
                    message = `AI settings updated: ${aiName} will control everything in Single AI Mode`;
                } else {
                    const playerAI = settings.playerAI === 'grok' ? 'Grok' : 'Claude 3.7 Sonnet';
                    const pokemonAI = settings.pokemonAI === 'grok' ? 'Grok' : 'Claude 3.7 Sonnet';
                    message = `AI settings updated: ${playerAI} as player AI, ${pokemonAI} as Pokémon AI in Dual Mode`;
                }
                addCommentary(message);
                
                currentAISettings = settings;
                saveAISettings();
                updateActiveAIDisplay(data.currentAI);
            } else {
                addCommentary(`Error updating AI settings: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error applying AI settings:', error);
            addCommentary('Error connecting to server. Please try again later.');
        });
}

// Update the active AI display
function updateActiveAIDisplay(aiName) {
    if (aiName) {
        activeAIName.textContent = aiName;
        
        // Highlight based on which AI is active
        const aiIndicator = document.getElementById('current-ai');
        if (aiName.toLowerCase().includes('grok')) {
            aiIndicator.className = 'ai-indicator grok-active';
        } else if (aiName.toLowerCase().includes('claude')) {
            aiIndicator.className = 'ai-indicator claude-active';
        } else {
            aiIndicator.className = 'ai-indicator';
        }
    } else {
        activeAIName.textContent = 'None';
        document.getElementById('current-ai').className = 'ai-indicator';
    }
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
    
    // Style the commentary based on which AI is speaking
    if (text.includes('[Grok]') || text.includes('[Grok as')) {
        commentaryItem.classList.add('grok-commentary');
    } else if (text.includes('[Claude]') || text.includes('[Claude as')) {
        commentaryItem.classList.add('claude-commentary');
    }
    
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
                addCommentary('Waiting for AI to start commenting...');
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
                
                // Apply the current AI settings when starting
                applyAISettings();
                
                addCommentary('Game started! Waiting for AI to make the first move...');
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
    addCommentary('Connected to Pokémon server!');
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
    
    // Update active AI if provided
    if (data.currentAI) {
        updateActiveAIDisplay(data.currentAI);
    }
});

socket.on('commentary_update', (data) => {
    addCommentary(data.text);
});

socket.on('ai_settings_update', (data) => {
    if (data.success) {
        playerAISelect.value = data.playerAI;
        pokemonAISelect.value = data.pokemonAI;
        aiModeSelect.value = data.mode;
        currentAISettings = {
            playerAI: data.playerAI,
            pokemonAI: data.pokemonAI,
            mode: data.mode
        };
        updateActiveAIDisplay(data.currentAI);
    }
});

// Event listeners
startButton.addEventListener('click', startGame);
stopButton.addEventListener('click', stopGame);
applyAISettingsButton.addEventListener('click', applyAISettings);

// Add event listener for mode change to update UI immediately
aiModeSelect.addEventListener('change', updateAIModeDisplay);

// Initialize the page on load
window.addEventListener('load', function() {
    initializePage();
    // Update UI based on initial AI mode
    updateAIModeDisplay();
}); 