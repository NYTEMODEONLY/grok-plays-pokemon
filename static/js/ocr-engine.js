/**
 * OCR Engine for Pokemon Red/Blue/Yellow
 * Uses Tesseract.js for text extraction from game screenshots
 * Optimized for Game Boy pixel fonts
 */

class OCREngine {
    constructor() {
        this.worker = null;
        this.isReady = false;
        this.isInitializing = false;
        this.lastOCRResult = null;
        this.lastScreenHash = null;
        this.ocrCache = new Map();
        this.cacheMaxSize = 50;
    }

    /**
     * Initialize Tesseract worker
     */
    async initialize() {
        if (this.isReady || this.isInitializing) {
            return;
        }

        this.isInitializing = true;

        try {
            // Check if Tesseract is loaded
            if (typeof Tesseract === 'undefined') {
                console.warn('Tesseract.js not loaded yet');
                this.isInitializing = false;
                return;
            }

            this.worker = await Tesseract.createWorker('eng', 1, {
                logger: m => {
                    if (m.status === 'recognizing text') {
                        // Progress updates
                    }
                }
            });

            // Set parameters optimized for pixel fonts
            await this.worker.setParameters({
                tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!?.,\'"-/:() ',
                tessedit_pageseg_mode: '6', // Assume uniform block of text
                preserve_interword_spaces: '1',
            });

            this.isReady = true;
            console.log('OCR Engine initialized');
        } catch (error) {
            console.error('Failed to initialize OCR:', error);
        }

        this.isInitializing = false;
    }

    /**
     * Calculate simple hash of canvas for caching
     */
    calculateCanvasHash(canvas) {
        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        const width = canvas.width;
        const height = canvas.height;

        // Sample pixels for hash
        let hash = 0;
        try {
            const data = ctx.getImageData(0, 0, width, height).data;
            for (let i = 0; i < data.length; i += 1000) {
                hash = ((hash << 5) - hash) + data[i];
                hash = hash & hash; // Convert to 32bit integer
            }
        } catch (e) {
            return null;
        }
        return hash;
    }

    /**
     * Extract text from canvas
     * @param {HTMLCanvasElement} canvas - The game canvas
     * @param {Object} region - Optional region to extract from { x, y, width, height } as percentages
     * @returns {Promise<Object>} { text: string, words: array, confidence: number }
     */
    async extractText(canvas, region = null) {
        if (!canvas) {
            return { text: '', words: [], confidence: 0 };
        }

        // Check cache
        const hash = this.calculateCanvasHash(canvas);
        if (hash && this.ocrCache.has(hash)) {
            return this.ocrCache.get(hash);
        }

        // Initialize if needed
        if (!this.isReady) {
            await this.initialize();
            if (!this.isReady) {
                return { text: '', words: [], confidence: 0, error: 'OCR not ready' };
            }
        }

        try {
            let imageSource = canvas;

            // If region specified, crop the canvas
            if (region) {
                const croppedCanvas = this.cropCanvas(canvas, region);
                if (croppedCanvas) {
                    imageSource = croppedCanvas;
                }
            }

            // Preprocess image for better OCR
            const processedCanvas = this.preprocessForOCR(imageSource);

            // Run OCR
            const result = await this.worker.recognize(processedCanvas);

            const ocrResult = {
                text: result.data.text.trim(),
                words: result.data.words.map(w => ({
                    text: w.text,
                    confidence: w.confidence,
                    bbox: w.bbox
                })),
                confidence: result.data.confidence
            };

            // Cache result
            if (hash) {
                this.ocrCache.set(hash, ocrResult);
                if (this.ocrCache.size > this.cacheMaxSize) {
                    const firstKey = this.ocrCache.keys().next().value;
                    this.ocrCache.delete(firstKey);
                }
            }

            this.lastOCRResult = ocrResult;
            return ocrResult;

        } catch (error) {
            console.error('OCR error:', error);
            return { text: '', words: [], confidence: 0, error: error.message };
        }
    }

    /**
     * Crop canvas to specific region
     */
    cropCanvas(canvas, region) {
        const { x = 0, y = 0, width = 1, height = 1 } = region;

        const cropX = Math.floor(canvas.width * x);
        const cropY = Math.floor(canvas.height * y);
        const cropWidth = Math.floor(canvas.width * width);
        const cropHeight = Math.floor(canvas.height * height);

        const croppedCanvas = document.createElement('canvas');
        croppedCanvas.width = cropWidth;
        croppedCanvas.height = cropHeight;

        const ctx = croppedCanvas.getContext('2d');
        ctx.drawImage(canvas, cropX, cropY, cropWidth, cropHeight, 0, 0, cropWidth, cropHeight);

        return croppedCanvas;
    }

    /**
     * Preprocess image for better OCR results
     * Game Boy uses limited colors, so we can enhance contrast
     */
    preprocessForOCR(canvas) {
        const processed = document.createElement('canvas');
        processed.width = canvas.width * 2;  // Scale up for better OCR
        processed.height = canvas.height * 2;

        const ctx = processed.getContext('2d');

        // Scale up with nearest-neighbor to preserve pixel art
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(canvas, 0, 0, processed.width, processed.height);

        // Get image data
        const imageData = ctx.getImageData(0, 0, processed.width, processed.height);
        const data = imageData.data;

        // Convert to high contrast black and white
        for (let i = 0; i < data.length; i += 4) {
            const brightness = (data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114);

            // Threshold for Pokemon's limited palette
            const threshold = 128;
            const value = brightness > threshold ? 255 : 0;

            data[i] = value;     // R
            data[i + 1] = value; // G
            data[i + 2] = value; // B
            // Alpha stays the same
        }

        ctx.putImageData(imageData, 0, 0);
        return processed;
    }

    /**
     * Extract text from dialog box region
     */
    async extractDialogText(canvas) {
        const dialogRegion = { x: 0.05, y: 0.65, width: 0.9, height: 0.3 };
        return await this.extractText(canvas, dialogRegion);
    }

    /**
     * Extract text from battle menu region
     */
    async extractBattleMenuText(canvas) {
        const menuRegion = { x: 0.5, y: 0.65, width: 0.45, height: 0.3 };
        return await this.extractText(canvas, menuRegion);
    }

    /**
     * Extract Pokemon name from battle (enemy)
     */
    async extractEnemyPokemonName(canvas) {
        const nameRegion = { x: 0.05, y: 0.02, width: 0.5, height: 0.12 };
        return await this.extractText(canvas, nameRegion);
    }

    /**
     * Extract Pokemon name from battle (player)
     */
    async extractPlayerPokemonName(canvas) {
        const nameRegion = { x: 0.45, y: 0.45, width: 0.5, height: 0.12 };
        return await this.extractText(canvas, nameRegion);
    }

    /**
     * Extract menu options from right side menu
     */
    async extractMenuOptions(canvas) {
        const menuRegion = { x: 0.55, y: 0.1, width: 0.4, height: 0.8 };
        return await this.extractText(canvas, menuRegion);
    }

    /**
     * Quick text detection - checks if there's likely text in a region
     * Uses pixel analysis instead of full OCR for speed
     */
    hasTextInRegion(canvas, region) {
        try {
            const croppedCanvas = this.cropCanvas(canvas, region);
            const ctx = croppedCanvas.getContext('2d');
            const imageData = ctx.getImageData(0, 0, croppedCanvas.width, croppedCanvas.height);
            const data = imageData.data;

            let darkPixels = 0;
            let lightPixels = 0;

            for (let i = 0; i < data.length; i += 4) {
                const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3;
                if (brightness < 100) {
                    darkPixels++;
                } else if (brightness > 180) {
                    lightPixels++;
                }
            }

            // Text regions have both dark (text) and light (background) pixels
            const total = data.length / 4;
            const darkRatio = darkPixels / total;
            const lightRatio = lightPixels / total;

            return darkRatio > 0.1 && darkRatio < 0.7 && lightRatio > 0.2;
        } catch (e) {
            return false;
        }
    }

    /**
     * Parse extracted text for common Pokemon patterns
     */
    parseGameText(text) {
        const parsed = {
            raw: text,
            pokemonNames: [],
            numbers: [],
            menuOptions: [],
            isQuestion: false,
            hasYesNo: false
        };

        if (!text) return parsed;

        const upperText = text.toUpperCase();

        // Check for Yes/No
        if (upperText.includes('YES') || upperText.includes('NO')) {
            parsed.hasYesNo = true;
        }

        // Check if it's a question
        if (text.includes('?')) {
            parsed.isQuestion = true;
        }

        // Extract numbers (HP, levels, etc.)
        const numbers = text.match(/\d+/g);
        if (numbers) {
            parsed.numbers = numbers.map(n => parseInt(n));
        }

        // Common menu options
        const menuKeywords = ['FIGHT', 'PKMN', 'ITEM', 'RUN', 'POKEMON', 'BAG', 'SAVE', 'OPTION', 'EXIT'];
        for (const keyword of menuKeywords) {
            if (upperText.includes(keyword)) {
                parsed.menuOptions.push(keyword);
            }
        }

        // Try to extract Pokemon names (common starters and early game Pokemon)
        const pokemonNames = [
            'BULBASAUR', 'IVYSAUR', 'VENUSAUR',
            'CHARMANDER', 'CHARMELEON', 'CHARIZARD',
            'SQUIRTLE', 'WARTORTLE', 'BLASTOISE',
            'PIKACHU', 'RAICHU',
            'PIDGEY', 'PIDGEOTTO', 'PIDGEOT',
            'RATTATA', 'RATICATE',
            'CATERPIE', 'METAPOD', 'BUTTERFREE',
            'WEEDLE', 'KAKUNA', 'BEEDRILL',
            'NIDORAN', 'NIDORINO', 'NIDOKING', 'NIDORINA', 'NIDOQUEEN',
            'GEODUDE', 'GRAVELER', 'GOLEM',
            'ONIX', 'ZUBAT', 'GOLBAT'
        ];

        for (const pokemon of pokemonNames) {
            if (upperText.includes(pokemon)) {
                parsed.pokemonNames.push(pokemon);
            }
        }

        return parsed;
    }

    /**
     * Terminate the worker when done
     */
    async terminate() {
        if (this.worker) {
            await this.worker.terminate();
            this.worker = null;
            this.isReady = false;
        }
    }
}

// Export for use in browser
if (typeof window !== 'undefined') {
    window.OCREngine = OCREngine;
}
