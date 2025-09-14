// Voice Copilot Browser Extension - Content Script
// This script injects voice functionality into GitHub Copilot Chat

class VoiceCopilotInjector {
    constructor() {
        this.isInjected = false;
        this.recording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];

        this.init();
    }

    init() {
        // Wait for the page to fully load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.injectVoiceButton());
        } else {
            this.injectVoiceButton();
        }

        // Also watch for dynamic content changes (Copilot might load content dynamically)
        this.observeDOMChanges();
    }

    observeDOMChanges() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' && !this.isInjected) {
                    // Check if Copilot chat interface has loaded
                    const chatInput = this.findChatInput();
                    if (chatInput) {
                        this.injectVoiceButton();
                    }
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    findChatInput() {
        // Look for Copilot chat input field
        const selectors = [
            'textarea[data-testid="chat-input"]',
            'textarea[placeholder*="Ask Copilot"]',
            'textarea[placeholder*="Message Copilot"]',
            '.chat-input textarea',
            '[data-testid*="chat"] textarea',
            'form textarea'
        ];

        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element) {
                return element;
            }
        }

        return null;
    }

    injectVoiceButton() {
        if (this.isInjected) return;

        const chatInput = this.findChatInput();
        if (!chatInput) return;

        // Find the input container
        const inputContainer = chatInput.closest('.chat-input, .input-container, form') ||
                              chatInput.parentElement;

        if (!inputContainer) return;

        // Create voice button
        const voiceButton = this.createVoiceButton();

        // Insert button next to the input
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'voice-copilot-container';
        buttonContainer.style.cssText = `
            position: relative;
            display: inline-block;
            margin-left: 8px;
        `;

        buttonContainer.appendChild(voiceButton);
        inputContainer.appendChild(buttonContainer);

        this.isInjected = true;
        console.log('🎤 Voice Copilot button injected successfully');
    }

    createVoiceButton() {
        const button = document.createElement('button');
        button.className = 'voice-copilot-button';
        button.innerHTML = '🎤';
        button.title = 'Voice Input (Ctrl+Shift+V)';
        button.style.cssText = `
            width: 32px;
            height: 32px;
            border-radius: 50%;
            border: 2px solid #007acc;
            background: white;
            color: #007acc;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        `;

        // Hover effects
        button.onmouseover = () => {
            button.style.background = '#007acc';
            button.style.color = 'white';
            button.style.transform = 'scale(1.05)';
        };

        button.onmouseout = () => {
            if (!this.recording) {
                button.style.background = 'white';
                button.style.color = '#007acc';
                button.style.transform = 'scale(1)';
            }
        };

        // Click handler
        button.onclick = () => this.toggleRecording(button);

        return button;
    }

    async toggleRecording(button) {
        if (this.recording) {
            await this.stopRecording(button);
        } else {
            await this.startRecording(button);
        }
    }

    async startRecording(button) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                await this.processRecording(button);
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start(100); // Collect data every 100ms
            this.recording = true;

            this.updateButtonState(button, true);
            this.showNotification('🎤 Recording... Click to stop');

        } catch (error) {
            console.error('Recording failed:', error);
            this.showNotification('❌ Microphone access denied');
        }
    }

    async stopRecording(button) {
        if (this.mediaRecorder && this.recording) {
            this.mediaRecorder.stop();
            this.recording = false;
            this.updateButtonState(button, false);
        }
    }

    async processRecording(button) {
        try {
            this.showNotification('⏳ Processing...');

            const audioBlob = new Blob(this.audioChunks, {
                type: 'audio/webm;codecs=opus'
            });

            // Convert to WAV for better compatibility
            const wavBlob = await this.convertToWav(audioBlob);

            // Send to ASR service
            const transcription = await this.transcribeAudio(wavBlob);

            if (transcription) {
                // Insert into chat input
                this.insertIntoChat(transcription);
                this.showNotification('✅ Transcribed! Press Enter to send to Copilot');
            } else {
                this.showNotification('❌ Transcription failed');
            }

        } catch (error) {
            console.error('Processing failed:', error);
            this.showNotification('❌ Processing failed');
        }
    }

    async convertToWav(audioBlob) {
        // Convert WebM to WAV (simplified version)
        // In production, you'd want a more robust conversion
        return new Blob([await audioBlob.arrayBuffer()], { type: 'audio/wav' });
    }

    async transcribeAudio(audioBlob) {
        try {
            // Get ASR URL from storage
            const config = await this.getConfig();
            const asrUrl = config.asrUrl || 'http://localhost:8000/transcribe';

            const formData = new FormData();
            formData.append('file', audioBlob, 'recording.wav');

            const response = await fetch(asrUrl, {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                return result.text;
            } else {
                throw new Error(`ASR failed: ${response.status}`);
            }

        } catch (error) {
            console.error('Transcription error:', error);
            return null;
        }
    }

    insertIntoChat(text) {
        const chatInput = this.findChatInput();
        if (chatInput) {
            chatInput.value = text;
            chatInput.focus();

            // Trigger input event to notify Copilot of the change
            const inputEvent = new Event('input', { bubbles: true });
            chatInput.dispatchEvent(inputEvent);
        }
    }

    updateButtonState(button, isRecording) {
        if (isRecording) {
            button.style.background = '#ff4444';
            button.style.color = 'white';
            button.style.animation = 'pulse 1s infinite';
            button.innerHTML = '⏹️';
        } else {
            button.style.background = 'white';
            button.style.color = '#007acc';
            button.style.animation = 'none';
            button.innerHTML = '🎤';
        }
    }

    showNotification(message) {
        // Remove existing notification
        const existing = document.querySelector('.voice-copilot-notification');
        if (existing) {
            existing.remove();
        }

        // Create notification
        const notification = document.createElement('div');
        notification.className = 'voice-copilot-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #007acc;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 10000;
            font-size: 14px;
            font-weight: 500;
            animation: slideIn 0.3s ease;
        `;

        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    async getConfig() {
        return new Promise((resolve) => {
            chrome.storage.sync.get({
                asrUrl: 'http://localhost:8000/transcribe',
                mcpEnabled: false,
                mcpUrl: 'http://localhost:3000/mcp'
            }, resolve);
        });
    }
}

// Global keyboard shortcut
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'V') {
        e.preventDefault();

        // Find and click the voice button
        const voiceButton = document.querySelector('.voice-copilot-button');
        if (voiceButton) {
            voiceButton.click();
        }
    }
});

// Initialize the injector
const voiceInjector = new VoiceCopilotInjector();

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }

    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }

    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }

    .voice-copilot-button:hover {
        box-shadow: 0 4px 8px rgba(0,122,204,0.3) !important;
    }

    .voice-copilot-button:active {
        transform: scale(0.95) !important;
    }
`;
document.head.appendChild(style);

console.log('🎤 Voice Copilot extension loaded');