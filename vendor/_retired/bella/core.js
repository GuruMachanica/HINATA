// core.js - Bella's Brain (v3)
// Bella's core AI logic, supporting a hybrid architecture of local models and cloud APIs

import { pipeline, env, AutoTokenizer, AutoModelForSpeechSeq2Seq } from './vendor/transformers.js';
import CloudAPIService from './cloudAPI.js';

// Local model configuration
env.allowLocalModels = true;
env.useBrowserCache = false;
env.allowRemoteModels = false;
env.backends.onnx.logLevel = 'verbose';
env.localModelPath = './models/';


class BellaAI {
    static instance = null;

    static async getInstance() {
        if (this.instance === null) {
            this.instance = new BellaAI();
            await this.instance.init();
        }
        return this.instance;
    }

    constructor() {
        this.cloudAPI = new CloudAPIService();
        this.useCloudAPI = false; // Default to using local model
        this.currentMode = 'casual'; // Chat modes: casual, assistant, creative
    }

    async init() {
        console.log('Initializing Bella\'s core AI...');
        
        // Priority loading of LLM model (chat functionality)
        try {
            console.log('Loading LLM model...');
            this.llm = await pipeline('text2text-generation', 'Xenova/LaMini-Flan-T5-77M');
            console.log('LLM model loaded successfully.');
        } catch (error) {
            console.error('Failed to load LLM model:', error);
            // LLM loading failure doesn't block initialization
        }
        
        // Attempt to load ASR model (voice recognition)
        try {
            console.log('Loading ASR model...');
            const modelPath = 'Xenova/whisper-asr';
            const tokenizer = await AutoTokenizer.from_pretrained(modelPath);
            const model = await AutoModelForSpeechSeq2Seq.from_pretrained(modelPath);
            this.asr = await pipeline('automatic-speech-recognition', model, { tokenizer });
            console.log('ASR model loaded successfully.');
        } catch (error) {
            console.warn('ASR model failed to load, voice recognition will be disabled:', error);
            // ASR loading failure doesn't affect chat functionality
            this.asr = null;
        }

        // TTS model temporarily disabled
        // try {
        //     console.log('Loading TTS model...');
        //     this.tts = await pipeline('text-to-speech', 'Xenova/speecht5_tts', { quantized: false });
        //     console.log('TTS model loaded successfully.');
        // } catch (error) {
        //     console.warn('TTS model failed to load, voice synthesis will be disabled:', error);
        //     this.tts = null;
        // }

        console.log('Bella\'s core AI initialized successfully.');
    }

    async think(prompt) {
        try {
            // If cloud API is enabled and configured, use it as priority
            if (this.useCloudAPI && this.cloudAPI.isConfigured()) {
                return await this.thinkWithCloudAPI(prompt);
            }
            
            // Otherwise use local model
            return await this.thinkWithLocalModel(prompt);
            
        } catch (error) {
            console.error('Error during thinking process:', error);
            
            // If cloud API fails, try falling back to local model
            if (this.useCloudAPI) {
                console.log('Cloud API failed, falling back to local model...');
                try {
                    return await this.thinkWithLocalModel(prompt);
                } catch (localError) {
                    console.error('Local model also failed:', localError);
                }
            }
            
            return this.getErrorResponse();
        }
    }

    // Think using cloud API
    async thinkWithCloudAPI(prompt) {
        const enhancedPrompt = this.enhancePromptForMode(prompt);
        return await this.cloudAPI.chat(enhancedPrompt);
    }

    // Think using local model with optimized LLM parameters and processing
    async thinkWithLocalModel(prompt) {
        if (!this.llm) {
            return "I'm still learning how to think. Please wait a moment...";
        }
        
        const bellaPrompt = this.enhancePromptForMode(prompt, true);
        
        // Optimized LLM parameters for better responses
        const result = await this.llm(bellaPrompt, {
            max_new_tokens: 180,  // Increased token count for more complete responses
            temperature: 0.7,     // Slightly lowered temperature for better consistency
            top_k: 50,            // Increased top_k for more diverse vocabulary
            top_p: 0.92,          // Added top_p parameter to optimize sampling
            do_sample: true,      // Maintained sampling for creativity
            repetition_penalty: 1.2, // Added repetition penalty to avoid repetitive content
        });
        
        // Enhanced text cleaning and processing
        let response = result[0].generated_text;
        
        // Remove prompt part
        if (response.includes(bellaPrompt)) {
            response = response.replace(bellaPrompt, '').trim();
        }
        
        // Remove possible "Bella's response:" prefixes
        response = response.replace(/^(Bella's response:|Bella's professional response:|Bella's creative response:|Bella:)/i, '').trim();
        
        // If response is empty, provide backup responses
        if (!response || response.length < 2) {
            const backupResponses = [
                "That's an interesting question. Let me think about it for a moment...",
                "Good question! I need to organize my thoughts...",
                "I have some ideas, but let me put them together more coherently...",
                "This topic is fascinating. Let me consider how to respond...",
                "I'm thinking about different angles to this question. Just a moment..."
            ];
            return backupResponses[Math.floor(Math.random() * backupResponses.length)];
        }
        
        return response;
    }

    // Enhance prompts based on mode, using advanced LLM prompt engineering
    enhancePromptForMode(prompt, isLocal = false) {
        const modePrompts = {
            casual: isLocal ? 
                `As Bella, a friendly AI assistant similar to Siri, respond to the user in a warm, conversational tone. Your response should:
1. Be concise and helpful, like Siri's responses
2. Use natural, flowing language with a touch of personality
3. Be friendly but not overly emotional
4. Maintain a helpful, slightly witty tone
5. Sound intelligent and knowledgeable while remaining accessible

User message: ${prompt}
Bella's response:` :
                `You are Bella, an AI assistant similar to Siri. Respond in a helpful, concise manner with a touch of personality. Keep your responses clear and direct, while maintaining a friendly tone. Avoid overly technical language unless necessary, and focus on providing value to the user.

User message: ${prompt}
Bella's response:`,
            
            assistant: isLocal ?
                `As Bella, an intelligent AI assistant like Siri, provide accurate and helpful information. Your response should:
1. Deliver clear, factual information and useful advice
2. Organize content for easy understanding and application
3. Maintain a professional yet approachable tone
4. Use simple language when possible, technical terms only when necessary
5. Demonstrate expertise while remaining accessible

User question: ${prompt}
Bella's professional response:` :
                `You are Bella, a Siri-like AI assistant. Provide accurate, useful information and advice with a professional yet approachable tone. Organize your response clearly, avoid unnecessary technical language, and focus on being helpful and informative.

User question: ${prompt}
Bella's professional response:`,
            
            creative: isLocal ?
                `As Bella, a creative AI assistant with Siri-like qualities, use your imagination to respond. Your response should:
1. Present unique perspectives and creative thinking
2. Use vivid, descriptive language
3. Offer unexpected but interesting ideas
4. Inspire the user's imagination
5. Maintain a light, engaging tone

User prompt: ${prompt}
Bella's creative response:` :
                `You are Bella, a creative AI assistant with Siri-like qualities. Provide interesting, unique responses using vivid language and creative thinking. Offer unexpected perspectives that inspire imagination while maintaining an engaging, helpful tone.

User prompt: ${prompt}
Bella's creative response:`
        };
        
        return modePrompts[this.currentMode] || modePrompts.casual;
    }

    // Get error response
    getErrorResponse() {
        const errorResponses = [
            "I'm sorry, I'm having trouble processing that right now. Let me try to reorganize my thoughts...",
            "Hmm... I need to think about this a bit more. Please wait a moment.",
            "I seem to be having a bit of trouble with that. Give me a second to sort things out.",
            "Let me rephrase my thoughts. Just a moment please.",
            "I didn't quite catch that. Could you try asking in a different way?"
        ];
        
        return errorResponses[Math.floor(Math.random() * errorResponses.length)];
    }

    // Set chat mode
    setChatMode(mode) {
        if (['casual', 'assistant', 'creative'].includes(mode)) {
            this.currentMode = mode;
            return true;
        }
        return false;
    }

    // Switch AI service provider
    switchProvider(provider) {
        if (provider === 'local') {
            this.useCloudAPI = false;
            return true;
        } else {
            const success = this.cloudAPI.switchProvider(provider);
            if (success) {
                this.useCloudAPI = true;
            }
            return success;
        }
    }

    // Set API key
    setAPIKey(provider, apiKey) {
        return this.cloudAPI.setAPIKey(provider, apiKey);
    }

    // Clear conversation history
    clearHistory() {
        this.cloudAPI.clearHistory();
    }

    // Get current configuration
    getCurrentConfig() {
        return {
            useCloudAPI: this.useCloudAPI,
            provider: this.useCloudAPI ? this.cloudAPI.getCurrentProvider() : { name: 'local', model: 'LaMini-Flan-T5-77M' },
            mode: this.currentMode,
            isConfigured: this.useCloudAPI ? this.cloudAPI.isConfigured() : true
        };
    }

    // Process audio input
    async listen(audioData) {
        if (!this.asr) {
            throw new Error('Speech recognition model not initialized');
        }
        const result = await this.asr(audioData);
        return result.text;
    }

    // Generate speech from text
    async speak(text) {
        if (!this.tts) {
            throw new Error('Speech synthesis model not initialized');
        }
        // We need speaker embeddings for SpeechT5
        const speaker_embeddings = 'models/Xenova/speecht5_tts/speaker_embeddings.bin';
        const result = await this.tts(text, {
            speaker_embeddings,
        });
        return result.audio;
    }

    // Get cloud API service instance (for external access)
    getCloudAPIService() {
        return this.cloudAPI;
    }
}

// ES6 module export
export { BellaAI };