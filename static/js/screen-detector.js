/**
 * Screen Detector for Pokemon Red/Blue/Yellow
 * Uses pixel analysis to detect screen types without relying on AI vision
 *
 * Pokemon Game Boy screen is 160x144 pixels, but EmulatorJS scales it up
 */

class ScreenDetector {
    constructor() {
        // Game Boy color palette (approximate ranges)
        this.colors = {
            white: { r: [200, 255], g: [200, 255], b: [200, 255] },
            black: { r: [0, 60], g: [0, 60], b: [0, 60] },
            lightGray: { r: [150, 200], g: [150, 200], b: [150, 200] },
            darkGray: { r: [60, 150], g: [60, 150], b: [60, 150] },
        };

        // Screen regions (as percentages of total size)
        this.regions = {
            dialogBox: { y1: 0.65, y2: 0.95, x1: 0.05, x2: 0.95 },
            topHalf: { y1: 0.0, y2: 0.5, x1: 0.0, x2: 1.0 },
            bottomHalf: { y1: 0.5, y2: 1.0, x1: 0.0, x2: 1.0 },
            battleEnemy: { y1: 0.05, y2: 0.35, x1: 0.5, x2: 0.95 },
            battlePlayer: { y1: 0.35, y2: 0.65, x1: 0.05, x2: 0.5 },
            menuRight: { y1: 0.1, y2: 0.9, x1: 0.55, x2: 0.95 },
            titleLogo: { y1: 0.1, y2: 0.35, x1: 0.1, x2: 0.9 },
            nameGrid: { y1: 0.3, y2: 0.85, x1: 0.1, x2: 0.9 },
            hpBarArea: { y1: 0.15, y2: 0.35, x1: 0.5, x2: 0.95 },
        };

        this.lastScreenType = null;
        this.screenTypeConfidence = 0;
    }

    /**
     * Detect screen type from canvas
     * @param {HTMLCanvasElement} canvas - The game canvas
     * @returns {Object} { screenType: string, confidence: number, features: object }
     */
    detect(canvas) {
        // [DIAG] Log detection attempt
        console.log('[DIAG] detect() called with canvas:', canvas ? `${canvas.width}x${canvas.height}` : 'null');

        if (!canvas) {
            console.error('[DIAG] No canvas provided to detect()');
            return { screenType: 'unknown', confidence: 0, features: {}, error: 'no_canvas', errorMsg: 'Canvas element is null or undefined' };
        }

        if (canvas.width === 0 || canvas.height === 0) {
            console.error('[DIAG] Canvas has zero dimensions:', canvas.width, 'x', canvas.height);
            return { screenType: 'unknown', confidence: 0, features: {}, error: 'zero_dimensions', errorMsg: `Canvas is ${canvas.width}x${canvas.height}` };
        }

        const width = canvas.width;
        const height = canvas.height;

        // Get pixel data - handle both 2D and WebGL canvases
        let imageData;
        try {
            imageData = this.getPixelData(canvas, width, height);
            if (!imageData) {
                console.error('[DIAG] getPixelData returned null');
                return { screenType: 'unknown', confidence: 0, features: {}, error: 'no_pixel_data', errorMsg: 'Could not extract pixel data' };
            }
            console.log('[DIAG] getPixelData succeeded, data length:', imageData.data.length);
        } catch (e) {
            console.error('[DIAG] getPixelData FAILED:', e.name, e.message);
            return { screenType: 'unknown', confidence: 0, features: {}, error: 'pixel_extraction_failed', errorMsg: e.message };
        }

        const features = this.extractFeatures(imageData, width, height);
        console.log('[DIAG] Extracted features:', JSON.stringify(features));

        const screenType = this.classifyScreen(features);
        console.log('[DIAG] Classification result:', screenType.type, 'confidence:', screenType.confidence);

        this.lastScreenType = screenType.type;
        this.screenTypeConfidence = screenType.confidence;

        return {
            screenType: screenType.type,
            confidence: screenType.confidence,
            features: features
        };
    }

    /**
     * Get pixel data from canvas, handling both 2D and WebGL contexts
     * @param {HTMLCanvasElement} canvas - Source canvas (may be WebGL)
     * @param {number} width - Canvas width
     * @param {number} height - Canvas height
     * @returns {ImageData} Pixel data
     */
    getPixelData(canvas, width, height) {
        // First, try to get 2D context directly
        let ctx = canvas.getContext('2d', { willReadFrequently: true });

        if (ctx) {
            console.log('[DIAG] Using direct 2D context');
            return ctx.getImageData(0, 0, width, height);
        }

        // Canvas is likely WebGL - create temporary 2D canvas and copy
        console.log('[DIAG] 2D context unavailable, using temp canvas for WebGL');

        // Reuse temp canvas if already created, or create new one
        if (!this._tempCanvas) {
            this._tempCanvas = document.createElement('canvas');
        }

        const tempCanvas = this._tempCanvas;
        tempCanvas.width = width;
        tempCanvas.height = height;

        const tempCtx = tempCanvas.getContext('2d', { willReadFrequently: true });
        if (!tempCtx) {
            console.error('[DIAG] Failed to get temp canvas 2D context');
            return null;
        }

        // Draw the WebGL canvas onto our 2D temp canvas
        // This works because drawImage() can accept any canvas as source
        try {
            tempCtx.drawImage(canvas, 0, 0);
            console.log('[DIAG] Drew WebGL canvas to temp 2D canvas');
        } catch (e) {
            console.error('[DIAG] drawImage failed:', e.message);
            return null;
        }

        // Now read pixels from the temp canvas
        return tempCtx.getImageData(0, 0, width, height);
    }

    /**
     * Extract visual features from image data
     */
    extractFeatures(imageData, width, height) {
        const data = imageData.data;
        const features = {};

        // Check for dialog box (white bordered rectangle at bottom)
        features.hasDialogBox = this.detectDialogBox(data, width, height);

        // Check for battle screen indicators
        features.hasBattleUI = this.detectBattleUI(data, width, height);

        // Check for menu on right side
        features.hasRightMenu = this.detectRightMenu(data, width, height);

        // Check for name entry grid
        features.hasNameGrid = this.detectNameGrid(data, width, height);

        // Check for title screen
        features.isTitleScreen = this.detectTitleScreen(data, width, height);

        // Check for HP bars
        features.hasHPBars = this.detectHPBars(data, width, height);

        // Check for move list (4 moves in 2x2 grid)
        features.hasMoveList = this.detectMoveList(data, width, height);

        // Check for Yes/No prompt
        features.hasYesNoPrompt = this.detectYesNoPrompt(data, width, height);

        // Calculate overall brightness
        features.avgBrightness = this.calculateAverageBrightness(data);

        // Check if screen is mostly uniform (black/loading)
        features.isUniform = this.checkUniformity(data, width, height);

        return features;
    }

    /**
     * Detect white bordered dialog box at bottom of screen
     */
    detectDialogBox(data, width, height) {
        const region = this.regions.dialogBox;
        const startY = Math.floor(height * region.y1);
        const endY = Math.floor(height * region.y2);
        const startX = Math.floor(width * region.x1);
        const endX = Math.floor(width * region.x2);

        let whiteBorderPixels = 0;
        let darkInteriorPixels = 0;
        let totalChecked = 0;

        // Check top border of dialog region
        const borderY = startY;
        for (let x = startX; x < endX; x += 4) {
            const idx = (borderY * width + x) * 4;
            if (this.isWhitePixel(data, idx)) {
                whiteBorderPixels++;
            }
            totalChecked++;
        }

        // Check interior has darker pixels (text area)
        const interiorY = Math.floor((startY + endY) / 2);
        for (let x = startX + 20; x < endX - 20; x += 4) {
            const idx = (interiorY * width + x) * 4;
            if (!this.isWhitePixel(data, idx)) {
                darkInteriorPixels++;
            }
            totalChecked++;
        }

        const borderRatio = whiteBorderPixels / (totalChecked / 2);
        const hasWhiteBorder = borderRatio > 0.5;
        const hasDarkInterior = darkInteriorPixels > 10;

        return hasWhiteBorder && hasDarkInterior;
    }

    /**
     * Detect battle UI elements
     */
    detectBattleUI(data, width, height) {
        // Battle screen has:
        // 1. Enemy sprite area (top right)
        // 2. Player sprite area (bottom left)
        // 3. Battle menu box at bottom

        const enemyRegion = this.regions.battleEnemy;
        const playerRegion = this.regions.battlePlayer;

        // Check for sprite-like patterns (non-uniform areas with game colors)
        const enemyArea = this.getRegionStats(data, width, height, enemyRegion);
        const playerArea = this.getRegionStats(data, width, height, playerRegion);

        // Battle screen typically has distinct enemy/player areas with sprites
        const hasEnemySprite = enemyArea.variance > 1000 && !enemyArea.isUniform;
        const hasPlayerSprite = playerArea.variance > 1000 && !playerArea.isUniform;

        return hasEnemySprite && hasPlayerSprite;
    }

    /**
     * Detect menu on right side of screen
     */
    detectRightMenu(data, width, height) {
        const region = this.regions.menuRight;
        const startY = Math.floor(height * region.y1);
        const endY = Math.floor(height * region.y2);
        const startX = Math.floor(width * region.x1);
        const endX = Math.floor(width * region.x2);

        // Menu has a white/light background with dark text
        let lightPixels = 0;
        let totalPixels = 0;

        for (let y = startY; y < endY; y += 4) {
            for (let x = startX; x < endX; x += 4) {
                const idx = (y * width + x) * 4;
                if (this.isLightPixel(data, idx)) {
                    lightPixels++;
                }
                totalPixels++;
            }
        }

        // Menu should have a significant light background
        return (lightPixels / totalPixels) > 0.4;
    }

    /**
     * Detect name entry grid pattern
     */
    detectNameGrid(data, width, height) {
        const region = this.regions.nameGrid;
        const startY = Math.floor(height * region.y1);
        const endY = Math.floor(height * region.y2);
        const startX = Math.floor(width * region.x1);
        const endX = Math.floor(width * region.x2);

        // Name grid has regular repeating pattern of characters
        // Check for horizontal lines of similar brightness
        let horizontalLineCount = 0;

        for (let y = startY; y < endY; y += Math.floor(height * 0.08)) {
            let lightCount = 0;
            for (let x = startX; x < endX; x += 4) {
                const idx = (y * width + x) * 4;
                if (this.isLightPixel(data, idx)) {
                    lightCount++;
                }
            }
            if (lightCount > (endX - startX) / 8) {
                horizontalLineCount++;
            }
        }

        // Name entry grid typically has multiple rows
        return horizontalLineCount >= 4;
    }

    /**
     * Detect title screen
     */
    detectTitleScreen(data, width, height) {
        const region = this.regions.titleLogo;
        const stats = this.getRegionStats(data, width, height, region);

        // Title screen has large logo with specific pattern
        // Usually has high contrast and specific color distribution
        const bottomStats = this.getRegionStats(data, width, height, { y1: 0.85, y2: 0.95, x1: 0.1, x2: 0.9 });

        // Check for copyright text area at bottom (usually has text on dark background)
        const hasCopyrightArea = bottomStats.avgBrightness < 100 && bottomStats.variance < 5000;

        return stats.variance > 2000 && hasCopyrightArea;
    }

    /**
     * Detect HP bars in battle
     */
    detectHPBars(data, width, height) {
        const region = this.regions.hpBarArea;
        const startY = Math.floor(height * region.y1);
        const endY = Math.floor(height * region.y2);
        const startX = Math.floor(width * region.x1);
        const endX = Math.floor(width * region.x2);

        // HP bars are typically green/yellow/red horizontal lines
        let greenPixels = 0;
        let yellowPixels = 0;
        let redPixels = 0;

        for (let y = startY; y < endY; y += 2) {
            for (let x = startX; x < endX; x += 2) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];

                // Green HP bar
                if (g > r + 30 && g > b + 30 && g > 100) {
                    greenPixels++;
                }
                // Yellow HP bar
                if (r > 150 && g > 150 && b < 100) {
                    yellowPixels++;
                }
                // Red HP bar
                if (r > g + 50 && r > b + 50 && r > 150) {
                    redPixels++;
                }
            }
        }

        return (greenPixels + yellowPixels + redPixels) > 20;
    }

    /**
     * Detect move selection list
     */
    detectMoveList(data, width, height) {
        // Move list appears at bottom, shows 4 moves in 2x2 grid with PP
        const region = { y1: 0.65, y2: 0.95, x1: 0.05, x2: 0.55 };
        const stats = this.getRegionStats(data, width, height, region);

        // Move list has white/light background with text
        return stats.avgBrightness > 150 && stats.variance > 500 && stats.variance < 15000;
    }

    /**
     * Detect Yes/No prompt
     */
    detectYesNoPrompt(data, width, height) {
        // Yes/No is a small box, usually on right side
        const region = { y1: 0.3, y2: 0.5, x1: 0.6, x2: 0.9 };
        const stats = this.getRegionStats(data, width, height, region);

        // Small light box with minimal content
        return stats.avgBrightness > 180 && stats.variance < 3000;
    }

    /**
     * Get statistics for a screen region
     */
    getRegionStats(data, width, height, region) {
        const startY = Math.floor(height * region.y1);
        const endY = Math.floor(height * region.y2);
        const startX = Math.floor(width * region.x1);
        const endX = Math.floor(width * region.x2);

        let sum = 0;
        let sumSq = 0;
        let count = 0;
        let uniformRuns = 0;
        let lastBrightness = -1;

        for (let y = startY; y < endY; y += 2) {
            for (let x = startX; x < endX; x += 2) {
                const idx = (y * width + x) * 4;
                const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
                sum += brightness;
                sumSq += brightness * brightness;
                count++;

                if (Math.abs(brightness - lastBrightness) < 10) {
                    uniformRuns++;
                }
                lastBrightness = brightness;
            }
        }

        const avg = sum / count;
        const variance = (sumSq / count) - (avg * avg);
        const isUniform = (uniformRuns / count) > 0.8;

        return { avgBrightness: avg, variance: variance, isUniform: isUniform };
    }

    /**
     * Calculate average brightness of entire screen
     */
    calculateAverageBrightness(data) {
        let sum = 0;
        for (let i = 0; i < data.length; i += 16) {  // Sample every 4th pixel
            sum += (data[i] + data[i + 1] + data[i + 2]) / 3;
        }
        return sum / (data.length / 16);
    }

    /**
     * Check if screen is mostly uniform (loading/black screen)
     */
    checkUniformity(data, width, height) {
        const sample = [];
        for (let i = 0; i < data.length; i += width * 4 * 10) {
            sample.push((data[i] + data[i + 1] + data[i + 2]) / 3);
        }

        if (sample.length < 5) return true;

        const avg = sample.reduce((a, b) => a + b, 0) / sample.length;
        const variance = sample.reduce((a, b) => a + (b - avg) ** 2, 0) / sample.length;

        return variance < 100;
    }

    /**
     * Check if pixel is white/near-white
     */
    isWhitePixel(data, idx) {
        return data[idx] > 200 && data[idx + 1] > 200 && data[idx + 2] > 200;
    }

    /**
     * Check if pixel is light colored
     */
    isLightPixel(data, idx) {
        const brightness = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
        return brightness > 150;
    }

    /**
     * Classify screen based on extracted features
     */
    classifyScreen(features) {
        // Priority-based classification

        // Loading/black screen
        if (features.isUniform && features.avgBrightness < 30) {
            return { type: 'loading', confidence: 0.9 };
        }

        // Title screen
        if (features.isTitleScreen && !features.hasDialogBox && !features.hasBattleUI) {
            return { type: 'title', confidence: 0.8 };
        }

        // Name entry grid
        if (features.hasNameGrid && !features.hasBattleUI) {
            return { type: 'name_entry', confidence: 0.85 };
        }

        // Battle screen
        if (features.hasBattleUI && features.hasHPBars) {
            if (features.hasMoveList) {
                return { type: 'battle_move_select', confidence: 0.9 };
            }
            return { type: 'battle', confidence: 0.85 };
        }

        // Yes/No prompt
        if (features.hasYesNoPrompt && !features.hasBattleUI) {
            return { type: 'yes_no', confidence: 0.8 };
        }

        // Dialog box (most common)
        if (features.hasDialogBox) {
            return { type: 'dialog', confidence: 0.85 };
        }

        // Menu
        if (features.hasRightMenu && !features.hasBattleUI) {
            return { type: 'menu', confidence: 0.75 };
        }

        // Overworld (default when nothing else matches)
        if (!features.isUniform && features.avgBrightness > 50) {
            return { type: 'overworld', confidence: 0.6 };
        }

        return { type: 'unknown', confidence: 0.3 };
    }
}

// Export for use in browser
if (typeof window !== 'undefined') {
    window.ScreenDetector = ScreenDetector;
}
