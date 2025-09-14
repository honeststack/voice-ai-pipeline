// Voice Copilot Browser Extension - Popup Script

class VoiceCopilotPopup {
    constructor() {
        this.elements = {};
        this.init();
    }

    init() {
        this.cacheElements();
        this.setupEventListeners();
        this.loadSettings();
    }

    cacheElements() {
        this.elements = {
            asrUrl: document.getElementById('asrUrl'),
            mcpEnabled: document.getElementById('mcpEnabled'),
            mcpUrl: document.getElementById('mcpUrl'),
            mcpGroup: document.getElementById('mcpGroup'),
            autoPaste: document.getElementById('autoPaste'),
            saveBtn: document.getElementById('saveBtn'),
            testBtn: document.getElementById('testBtn'),
            status: document.getElementById('status')
        };
    }

    setupEventListeners() {
        // MCP toggle
        this.elements.mcpEnabled.addEventListener('change', (e) => {
            this.elements.mcpGroup.style.display = e.target.checked ? 'block' : 'none';
        });

        // Save settings
        this.elements.saveBtn.addEventListener('click', () => this.saveSettings());

        // Test connection
        this.elements.testBtn.addEventListener('click', () => this.testConnection());

        // Enter key in inputs
        [this.elements.asrUrl, this.elements.mcpUrl].forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.saveSettings();
                }
            });
        });
    }

    async loadSettings() {
        try {
            const settings = await this.getSettings();
            this.elements.asrUrl.value = settings.asrUrl || '';
            this.elements.mcpEnabled.checked = settings.mcpEnabled || false;
            this.elements.mcpUrl.value = settings.mcpUrl || '';
            this.elements.autoPaste.checked = settings.autoPaste || false;

            // Show/hide MCP group
            this.elements.mcpGroup.style.display = settings.mcpEnabled ? 'block' : 'none';
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.showStatus('Failed to load settings', 'error');
        }
    }

    async saveSettings() {
        try {
            const settings = {
                asrUrl: this.elements.asrUrl.value.trim(),
                mcpEnabled: this.elements.mcpEnabled.checked,
                mcpUrl: this.elements.mcpUrl.value.trim(),
                autoPaste: this.elements.autoPaste.checked
            };

            await this.setSettings(settings);
            this.showStatus('Settings saved successfully!', 'success');
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showStatus('Failed to save settings', 'error');
        }
    }

    async testConnection() {
        this.showStatus('Testing connection...', 'info');
        this.elements.testBtn.disabled = true;
        this.elements.testBtn.textContent = 'Testing...';

        try {
            const asrUrl = this.elements.asrUrl.value.trim();
            if (!asrUrl) {
                throw new Error('ASR URL is required');
            }

            // Test ASR service
            const response = await fetch(asrUrl.replace('/transcribe', '/health') || `${asrUrl}/health`, {
                method: 'GET',
                signal: AbortSignal.timeout(5000)
            });

            if (response.ok) {
                // Test MCP if enabled
                if (this.elements.mcpEnabled.checked) {
                    const mcpUrl = this.elements.mcpUrl.value.trim();
                    if (mcpUrl) {
                        await this.testMCPConnection(mcpUrl);
                    }
                }

                this.showStatus('✅ Connection successful!', 'success');
            } else {
                throw new Error(`ASR service returned ${response.status}`);
            }

        } catch (error) {
            console.error('Connection test failed:', error);
            this.showStatus(`❌ Connection failed: ${error.message}`, 'error');
        } finally {
            this.elements.testBtn.disabled = false;
            this.elements.testBtn.textContent = 'Test Connection';
        }
    }

    async testMCPConnection(mcpUrl) {
        try {
            // Simple MCP ping test
            const response = await fetch(mcpUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    id: 1,
                    method: 'ping',
                    params: {}
                }),
                signal: AbortSignal.timeout(3000)
            });

            if (!response.ok) {
                console.warn('MCP ping failed, but ASR is working');
            }
        } catch (error) {
            console.warn('MCP test failed:', error);
        }
    }

    getSettings() {
        return new Promise((resolve) => {
            chrome.storage.sync.get({
                asrUrl: 'http://localhost:8000/transcribe',
                mcpEnabled: false,
                mcpUrl: 'http://localhost:3000/mcp',
                autoPaste: true
            }, resolve);
        });
    }

    setSettings(settings) {
        return new Promise((resolve) => {
            chrome.storage.sync.set(settings, resolve);
        });
    }

    showStatus(message, type = 'info') {
        const statusEl = this.elements.status;
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
        statusEl.style.display = 'block';

        // Auto-hide after 3 seconds for success messages
        if (type === 'success') {
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 3000);
        }
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new VoiceCopilotPopup();
});

// Handle popup close
window.addEventListener('beforeunload', () => {
    // Cleanup if needed
});