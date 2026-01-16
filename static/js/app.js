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
const actionLogEl = document.getElementById('action-log');
const startButton = document.getElementById('start-button');
const stopButton = document.getElementById('stop-button');
const applyAISettingsButton = document.getElementById('apply-ai-settings');
const playerAISelect = document.getElementById('player-ai');
const pokemonAISelect = document.getElementById('pokemon-ai');
const aiModeSelect = document.getElementById('ai-mode');

// ROM Upload Elements
const romFileInput = document.getElementById('rom-file');
const uploadRomBtn = document.getElementById('upload-rom-btn');
const clearRomBtn = document.getElementById('clear-rom-btn');
const uploadStatus = document.getElementById('upload-status');
const currentRomInfo = document.getElementById('current-rom-info');
const currentRomName = document.getElementById('current-rom-name');
const romStatus = document.getElementById('rom-status');

// Game state
let gameRunning = false;
let isAutonomous = false;
let playtimeInterval = null;
let localPlaytimeSeconds = 0;
let currentAISettings = {
    playerAI: 'grok',
    pokemonAI: 'claude',
    mode: 'dual'
};

// Playtime Elements
const playtimeDisplay = document.getElementById('playtime-display');
const totalActionsEl = document.getElementById('total-actions');
const actionsPerMinuteEl = document.getElementById('actions-per-minute');
const autonomousBadge = document.getElementById('autonomous-badge');

// ROM Upload Functions
function uploadRom() {
    const file = romFileInput.files[0];
    if (!file) {
        showUploadStatus('Please select a ROM file first.', 'warning');
        return;
    }

    // Check file size (5MB limit)
    const maxSize = 5 * 1024 * 1024; // 5MB in bytes
    if (file.size > maxSize) {
        showUploadStatus(`File is too large. Maximum size is 5MB. Your file is ${(file.size / 1024 / 1024).toFixed(2)}MB.`, 'danger');
        return;
    }

    const formData = new FormData();
    formData.append('rom', file);

    uploadRomBtn.disabled = true;
    uploadRomBtn.textContent = 'Uploading...';
    showUploadStatus(`Uploading ROM... (${(file.size / 1024 / 1024).toFixed(2)}MB)`, 'info');

    fetch('/api/upload_rom', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 413) {
                throw new Error('File is too large for the server. Please try a smaller file or contact the administrator.');
            }
            throw new Error(`Server error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showUploadStatus(`Successfully uploaded ${data.rom_name}! (${(data.file_size / 1024 / 1024).toFixed(2)}MB)`, 'success');
            updateRomInfo(data.rom_name, 'Ready');
            addCommentary(`ROM uploaded: ${data.rom_name}`);
        } else {
            showUploadStatus(data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error uploading ROM:', error);
        showUploadStatus(error.message || 'Error uploading ROM. Please try again.', 'danger');
    })
    .finally(() => {
        uploadRomBtn.disabled = false;
        uploadRomBtn.textContent = 'Upload ROM';
    });
}

function clearRom() {
    fetch('/api/upload_rom', {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateRomInfo(null, 'No ROM');
            showUploadStatus('ROM cleared successfully.', 'success');
            addCommentary('ROM cleared');
        } else {
            showUploadStatus(data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error clearing ROM:', error);
        showUploadStatus('Error clearing ROM. Please try again.', 'danger');
    });
}

function showUploadStatus(message, type) {
    uploadStatus.innerHTML = `<div class="alert alert-${type} mt-2">${message}</div>`;
    setTimeout(() => {
        uploadStatus.innerHTML = '';
    }, 5000);
}

function updateRomInfo(romName, status) {
    if (romName) {
        currentRomName.textContent = romName;
        romStatus.textContent = status;
        currentRomInfo.style.display = 'block';
    } else {
        currentRomInfo.style.display = 'none';
    }
}

// Playtime Functions
function formatPlaytime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updatePlaytimeDisplay() {
    if (gameRunning) {
        localPlaytimeSeconds++;
        if (playtimeDisplay) {
            playtimeDisplay.textContent = formatPlaytime(localPlaytimeSeconds);
        }
    }
}

function startPlaytimeCounter() {
    if (!playtimeInterval) {
        playtimeInterval = setInterval(updatePlaytimeDisplay, 1000);
    }
}

function stopPlaytimeCounter() {
    if (playtimeInterval) {
        clearInterval(playtimeInterval);
        playtimeInterval = null;
    }
}

function fetchGameplayStats() {
    fetch('/api/gameplay_stats')
        .then(response => response.json())
        .then(data => {
            // Sync playtime with server
            localPlaytimeSeconds = data.playtime_seconds;
            if (playtimeDisplay) {
                playtimeDisplay.textContent = data.playtime_formatted;
            }

            // Update stats
            if (totalActionsEl) {
                totalActionsEl.textContent = data.total_actions;
            }
            if (actionsPerMinuteEl) {
                actionsPerMinuteEl.textContent = data.actions_per_minute.toFixed(1);
            }

            // Update autonomous badge
            isAutonomous = data.is_autonomous;
            if (autonomousBadge) {
                autonomousBadge.style.display = isAutonomous ? 'inline-block' : 'none';
            }

            // Update API status
            updateAPIStatus(data.api_available);
        })
        .catch(error => {
            console.error('Error fetching gameplay stats:', error);
        });
}

function updateAPIStatus(isAvailable) {
    const apiStatusEl = document.getElementById('api-status');
    const apiStatusText = document.getElementById('api-status-text');

    if (apiStatusEl) {
        apiStatusEl.style.display = 'flex';

        if (isAvailable) {
            apiStatusEl.className = 'api-status connected';
            if (apiStatusText) apiStatusText.textContent = 'xAI API: Connected';
        } else {
            apiStatusEl.className = 'api-status disconnected';
            if (apiStatusText) apiStatusText.textContent = 'xAI API: Not configured (set XAI_API_KEY)';
        }
    }
}

// Action Log Functions
function fetchActionLog() {
    fetch('/api/action_log')
        .then(response => response.json())
        .then(data => {
            updateActionLog(data);
        })
        .catch(error => {
            console.error('Error fetching action log:', error);
        });
}

function updateActionLog(actions) {
    if (!actions || actions.length === 0) {
        actionLogEl.innerHTML = '<p class="action-log-item">Waiting for actions...</p>';
        return;
    }

    actionLogEl.innerHTML = '';
    // Show last 20 actions
    const recentActions = actions.slice(-20);

    recentActions.forEach(action => {
        const actionItem = document.createElement('p');
        actionItem.className = 'action-log-item';

        const timestamp = new Date(action.timestamp * 1000);
        const timeString = timestamp.toLocaleTimeString();

        actionItem.innerHTML = `
            <small class="text-muted">${timeString}</small><br>
            <strong>${action.action.toUpperCase()}</strong>
            ${action.commentary ? `<br><em>${action.commentary}</em>` : ''}
        `;
        actionLogEl.appendChild(actionItem);
    });

    actionLogEl.scrollTop = actionLogEl.scrollHeight; // Auto-scroll to bottom
}

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
                fetchActionLog();
                fetchAISettings();
                fetchGameplayStats();
                startPlaytimeCounter();
            } else {
                // Still fetch gameplay stats to check API status
                fetchGameplayStats();
            }

            // Start periodic stats updates
            setInterval(fetchGameplayStats, 5000);

            // Update ROM info
            if (data.rom_info && data.rom_info.rom_exists) {
                updateRomInfo(data.rom_info.rom_name, 'Ready');
            } else {
                updateRomInfo(null, 'No ROM');
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

// Fetch both commentary and action log
function fetchCommentaryAndActions() {
    fetchCommentary();
    fetchActionLog();
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
                localPlaytimeSeconds = 0;
                updateControlButtons();
                startPlaytimeCounter();

                // Apply the current AI settings when starting
                applyAISettings();

                // Start fetching stats periodically
                setInterval(fetchGameplayStats, 5000);

                addCommentary('Game started! Grok is now playing Pokemon autonomously...');
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
                stopPlaytimeCounter();
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
    locationEl.textContent = data.location || 'Unknown';
    badgesEl.textContent = data.badges || 0;
    moneyEl.textContent = (data.money || 0).toLocaleString();

    // Update badge icons
    updateBadgeIcons(data.badges || 0);

    // Update battle info
    updateBattleInfo(data.in_battle, data.enemy);

    // Update active AI if provided
    if (data.currentAI) {
        updateActiveAIDisplay(data.currentAI);
    }
});

// Update badge icons display
function updateBadgeIcons(badgeCount) {
    const badgeIconsEl = document.getElementById('badge-icons');
    if (badgeIconsEl) {
        let icons = '';
        for (let i = 0; i < 8; i++) {
            const earned = i < badgeCount ? 'earned' : 'not-earned';
            icons += `<span class="badge-icon ${earned}"></span>`;
        }
        badgeIconsEl.innerHTML = icons;
    }
}

// Update battle info display
function updateBattleInfo(inBattle, enemy) {
    const battleInfoEl = document.getElementById('battle-info');
    const enemyNameEl = document.getElementById('enemy-name');
    const enemyLevelEl = document.getElementById('enemy-level');

    if (battleInfoEl) {
        if (inBattle && enemy) {
            battleInfoEl.style.display = 'block';
            if (enemyNameEl) enemyNameEl.textContent = enemy.name || '???';
            if (enemyLevelEl) enemyLevelEl.textContent = enemy.level || '?';
        } else {
            battleInfoEl.style.display = 'none';
        }
    }
}

socket.on('commentary_update', (data) => {
    addCommentary(data.text);
    // Also update action log when commentary is received
    fetchActionLog();
});

socket.on('action_update', (data) => {
    // Update action count in real-time
    if (totalActionsEl) {
        const currentCount = parseInt(totalActionsEl.textContent) || 0;
        totalActionsEl.textContent = currentCount + 1;
    }
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

// ROM upload event listeners
uploadRomBtn.addEventListener('click', uploadRom);
clearRomBtn.addEventListener('click', clearRom);

// Add event listener for mode change to update UI immediately
aiModeSelect.addEventListener('change', updateAIModeDisplay);

// Initialize the page on load
window.addEventListener('load', function() {
    initializePage();
    // Update UI based on initial AI mode
    updateAIModeDisplay();
}); 