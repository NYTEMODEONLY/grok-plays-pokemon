/**
 * Browser-based Game Boy Emulator wrapper for Grok Plays Pokemon
 * Uses EmulatorJS for in-browser emulation
 */

class BrowserEmulator {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.isRunning = false;
        this.frameCount = 0;
        this.emulator = null;
        this.romLoaded = false;

        // Game state (will be updated by reading from emulator memory)
        this.gameState = {
            pokemon_team: [],
            items: [],
            location: "Unknown",
            badges: 0,
            money: 0,
            in_battle: false,
            enemy: null
        };

        // Button mapping for EmulatorJS
        this.buttonMap = {
            'a': 'a',
            'b': 'b',
            'start': 'start',
            'select': 'select',
            'up': 'up',
            'down': 'down',
            'left': 'left',
            'right': 'right'
        };
    }

    async loadROM(romData) {
        // This will be configured to use EmulatorJS
        // EmulatorJS is a browser-based emulator that supports Game Boy
        console.log('Loading ROM into browser emulator...');
        this.romLoaded = true;
        return true;
    }

    start() {
        if (!this.romLoaded) {
            console.error('No ROM loaded');
            return false;
        }
        this.isRunning = true;
        console.log('Emulator started');
        return true;
    }

    stop() {
        this.isRunning = false;
        console.log('Emulator stopped');
    }

    pressButton(button) {
        if (!this.isRunning) return false;

        const mappedButton = this.buttonMap[button.toLowerCase()];
        if (!mappedButton) {
            console.warn('Unknown button:', button);
            return false;
        }

        // Send button press to EmulatorJS
        if (this.emulator && this.emulator.gameManager) {
            this.emulator.gameManager.simulateInput(0, mappedButton, true);
            setTimeout(() => {
                this.emulator.gameManager.simulateInput(0, mappedButton, false);
            }, 100);
        }

        this.frameCount++;
        return true;
    }

    getScreenshot() {
        if (!this.canvas) return null;
        return this.canvas.toDataURL('image/png');
    }

    getScreenshotBase64() {
        const dataUrl = this.getScreenshot();
        if (!dataUrl) return null;
        // Remove the data:image/png;base64, prefix
        return dataUrl.split(',')[1];
    }

    getState() {
        return this.gameState;
    }

    updateState(newState) {
        this.gameState = { ...this.gameState, ...newState };
    }
}

/**
 * Autonomous AI Controller for browser-based emulation
 */
class BrowserAIController {
    constructor(emulator, apiEndpoint = '/api/action') {
        this.emulator = emulator;
        this.apiEndpoint = apiEndpoint;
        this.isRunning = false;
        this.isPaused = false;
        this.actionDelay = 2000; // 2 seconds between actions
        this.recentActions = [];
        this.totalActions = 0;
        this.startTime = null;
        this.loopInterval = null;

        // Callbacks for UI updates
        this.onAction = null;
        this.onCommentary = null;
        this.onStateUpdate = null;
        this.onError = null;
    }

    start() {
        if (this.isRunning) return;

        this.isRunning = true;
        this.isPaused = false;
        this.startTime = Date.now();

        this.loopInterval = setInterval(() => this.gameLoop(), this.actionDelay);
        console.log('AI Controller started');

        if (this.onCommentary) {
            this.onCommentary('Grok is now playing Pokemon autonomously!');
        }
    }

    stop() {
        this.isRunning = false;
        if (this.loopInterval) {
            clearInterval(this.loopInterval);
            this.loopInterval = null;
        }
        console.log('AI Controller stopped');

        if (this.onCommentary) {
            this.onCommentary('Grok has stopped playing.');
        }
    }

    pause() {
        this.isPaused = true;
        if (this.onCommentary) {
            this.onCommentary('Grok is taking a break...');
        }
    }

    resume() {
        this.isPaused = false;
        if (this.onCommentary) {
            this.onCommentary('Grok is back to playing!');
        }
    }

    async gameLoop() {
        if (!this.isRunning || this.isPaused) return;
        if (!this.emulator || !this.emulator.isRunning) return;

        try {
            // Get screenshot
            const screenshot = this.emulator.getScreenshotBase64();
            if (!screenshot) {
                console.warn('Could not get screenshot');
                return;
            }

            // Get current game state
            const gameState = this.emulator.getState();

            // Call API for AI decision
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    screenshot: screenshot,
                    game_state: gameState,
                    recent_actions: this.recentActions.slice(-10)
                })
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const result = await response.json();

            if (result.error) {
                if (this.onError) {
                    this.onError(result.error);
                }
                return;
            }

            // Execute the action
            const action = result.action || 'a';
            const commentary = result.commentary || 'Making a move...';
            const confidence = result.confidence || 0.5;

            this.emulator.pressButton(action);

            // Track action
            this.recentActions.push(action);
            if (this.recentActions.length > 50) {
                this.recentActions.shift();
            }
            this.totalActions++;

            // Callbacks
            if (this.onAction) {
                this.onAction(action, commentary, confidence);
            }
            if (this.onCommentary) {
                this.onCommentary(`[Grok] ${commentary}`);
            }
            if (this.onStateUpdate) {
                this.onStateUpdate(gameState);
            }

        } catch (error) {
            console.error('Error in game loop:', error);
            if (this.onError) {
                this.onError(error.message);
            }
        }
    }

    getStats() {
        const playtimeMs = this.startTime ? Date.now() - this.startTime : 0;
        const playtimeSeconds = Math.floor(playtimeMs / 1000);
        const minutes = playtimeSeconds / 60;

        return {
            isRunning: this.isRunning,
            isPaused: this.isPaused,
            totalActions: this.totalActions,
            actionsPerMinute: minutes > 0 ? (this.totalActions / minutes).toFixed(1) : 0,
            playtimeSeconds: playtimeSeconds,
            playtimeFormatted: this.formatPlaytime(playtimeSeconds)
        };
    }

    formatPlaytime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    setActionDelay(ms) {
        this.actionDelay = Math.max(1000, Math.min(10000, ms));
        if (this.loopInterval) {
            clearInterval(this.loopInterval);
            this.loopInterval = setInterval(() => this.gameLoop(), this.actionDelay);
        }
    }
}

// Export for use
window.BrowserEmulator = BrowserEmulator;
window.BrowserAIController = BrowserAIController;
