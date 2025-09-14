import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import axios, { AxiosResponse } from 'axios';
import * as FormData from 'form-data';

interface MCPRequest {
    jsonrpc: string;
    id: number;
    method: string;
    params: any;
}

interface MCPResponse {
    jsonrpc: string;
    id: number;
    result?: any;
    error?: any;
}

interface ASRResponse {
    text: string;
    confidence?: number;
}

interface MediaRecorderMock {
    start: () => void;
    stop: () => void;
    ondataavailable: ((event: any) => void) | null;
    onstop: (() => void) | null;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('🎤 Voice Copilot MCP extension is now active!');

    // Initialize the extension
    const voiceCopilot = new VoiceCopilotExtension(context);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('voiceCopilot.startRecording', () => voiceCopilot.startRecording()),
        vscode.commands.registerCommand('voiceCopilot.stopRecording', () => voiceCopilot.stopRecording()),
        vscode.commands.registerCommand('voiceCopilot.configure', () => voiceCopilot.showConfiguration()),
        vscode.commands.registerCommand('voiceCopilot.testConnection', () => voiceCopilot.testConnection())
    );

    // Create status bar item
    voiceCopilot.createStatusBarItem();

    // Register tree data provider for explorer view
    vscode.window.registerTreeDataProvider('voiceCopilotExplorer', new VoiceCopilotProvider());
}

export function deactivate() {
    console.log('🎤 Voice Copilot MCP extension deactivated');
}

class VoiceCopilotExtension {
    private context: vscode.ExtensionContext;
    private statusBarItem: vscode.StatusBarItem;
    private isRecording: boolean = false;
    private recordingTimeout: NodeJS.Timeout | null = null;
    private mediaRecorder: any = null;
    private audioChunks: Blob[] = [];

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
    }

    createStatusBarItem() {
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.command = 'voiceCopilot.startRecording';
        this.updateStatusBar();
        this.statusBarItem.show();
    }

    updateStatusBar() {
        const config = vscode.workspace.getConfiguration('voiceCopilot');
        if (!config.get('ui.showStatusBar', true)) {
            this.statusBarItem.hide();
            return;
        }

        if (this.isRecording) {
            this.statusBarItem.text = '$(record) Recording...';
            this.statusBarItem.color = '#ff4444';
            this.statusBarItem.tooltip = 'Click to stop recording';
        } else {
            this.statusBarItem.text = '$(mic) Voice';
            this.statusBarItem.color = undefined;
            this.statusBarItem.tooltip = 'Click to start voice recording (Ctrl+Shift+V)';
        }
    }

    async startRecording() {
        if (this.isRecording) {
            this.stopRecording();
            return;
        }

        try {
            // Request microphone permission and start recording
            await this.initializeRecording();

            this.isRecording = true;
            this.updateStatusBar();

            // Set maximum recording duration
            const config = vscode.workspace.getConfiguration('voiceCopilot');
            const maxDuration = config.get('recording.maxDuration', 30) * 1000;

            this.recordingTimeout = setTimeout(() => {
                if (this.isRecording) {
                    this.stopRecording();
                }
            }, maxDuration);

            // Show notification
            if (config.get('ui.notifications', true)) {
                vscode.window.showInformationMessage('🎤 Voice recording started. Click status bar or press Ctrl+Shift+V again to stop.');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`Failed to start recording: ${error}`);
        }
    }

    async initializeRecording() {
        // This would use Web Audio API in a webview or Node.js audio libraries
        // For now, we'll simulate the recording process
        console.log('🎤 Initializing voice recording...');

        // In a real implementation, this would:
        // 1. Request microphone permission
        // 2. Initialize MediaRecorder
        // 3. Start recording audio chunks

        // For demonstration, we'll create a mock recording
        this.audioChunks = [];
        this.mediaRecorder = {
            start: () => console.log('Mock recording started'),
            stop: () => console.log('Mock recording stopped'),
            ondataavailable: null,
            onstop: null
        };
    }

    async stopRecording() {
        if (!this.isRecording) return;

        this.isRecording = false;

        if (this.recordingTimeout) {
            clearTimeout(this.recordingTimeout);
            this.recordingTimeout = null;
        }

        this.updateStatusBar();

        try {
            // Stop the media recorder
            if (this.mediaRecorder) {
                this.mediaRecorder.stop();
            }

            // Process the recording
            await this.processRecording();

        } catch (error) {
            vscode.window.showErrorMessage(`Failed to process recording: ${error}`);
        }
    }

    async processRecording() {
        try {
            vscode.window.showInformationMessage('⏳ Processing voice recording...');

            // Simulate audio processing delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Create mock audio data (in real implementation, this would be actual audio)
            const mockAudioData = Buffer.from('mock audio data');

            // Transcribe the audio
            const transcription = await this.transcribeAudio(mockAudioData);

            if (transcription) {
                // Insert into active editor or send to Copilot
                await this.handleTranscription(transcription);
                vscode.window.showInformationMessage('✅ Voice transcribed successfully!');
            } else {
                vscode.window.showWarningMessage('⚠️ Transcription failed');
            }

        } catch (error) {
            vscode.window.showErrorMessage(`Processing failed: ${error}`);
        }
    }

    async transcribeAudio(audioData: Buffer): Promise<string | null> {
        try {
            const config = vscode.workspace.getConfiguration('voiceCopilot');
            const asrUrl = config.get('asr.url', 'http://localhost:8000/transcribe');

            // Create form data for the audio file
            const formData = new FormData();
            formData.append('file', audioData, {
                filename: 'recording.wav',
                contentType: 'audio/wav'
            });

            const response = await axios.post(asrUrl, formData, {
                headers: formData.getHeaders(),
                timeout: config.get('asr.timeout', 30) * 1000
            });

            if (response.data && response.data.text) {
                return response.data.text.trim();
            }

            return null;

        } catch (error) {
            console.error('ASR transcription failed:', error);
            throw new Error(`ASR service error: ${error.message}`);
        }
    }

    async handleTranscription(transcription: string) {
        const config = vscode.workspace.getConfiguration('voiceCopilot');

        // Check if MCP is enabled
        if (config.get('mcp.enabled', false)) {
            await this.sendToCopilot(transcription);
        } else {
            // Insert into active editor
            await this.insertIntoEditor(transcription);
        }
    }

    async sendToCopilot(transcription: string) {
        try {
            const config = vscode.workspace.getConfiguration('voiceCopilot');
            const mcpUrl = config.get('mcp.url', 'http://localhost:3000/mcp');

            // Format as MCP request
            const mcpRequest = {
                jsonrpc: '2.0',
                id: Date.now(),
                method: 'copilot/chat',
                params: {
                    messages: [{
                        role: 'user',
                        content: transcription
                    }],
                    options: {
                        temperature: 0.7,
                        max_tokens: 1000
                    }
                }
            };

            const response = await axios.post(mcpUrl, mcpRequest, {
                headers: { 'Content-Type': 'application/json' },
                timeout: 30000
            });

            if (response.data && response.data.result) {
                // Show Copilot response
                const result = response.data.result;
                vscode.window.showInformationMessage(`🤖 Copilot: ${result.substring(0, 100)}${result.length > 100 ? '...' : ''}`);

                // Optionally insert into editor
                const insertResponse = await vscode.window.showQuickPick(['Yes', 'No'], {
                    placeHolder: 'Insert Copilot response into editor?'
                });

                if (insertResponse === 'Yes') {
                    await this.insertIntoEditor(result);
                }
            }

        } catch (error) {
            console.error('MCP request failed:', error);
            vscode.window.showErrorMessage(`MCP request failed: ${error.message}`);

            // Fallback to inserting transcription
            await this.insertIntoEditor(transcription);
        }
    }

    async insertIntoEditor(text: string) {
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showWarningMessage('No active editor found');
            return;
        }

        // Insert at cursor position
        const position = activeEditor.selection.active;
        await activeEditor.edit(editBuilder => {
            editBuilder.insert(position, text);
        });

        // Move cursor to end of inserted text
        const newPosition = position.translate(0, text.length);
        activeEditor.selection = new vscode.Selection(newPosition, newPosition);
    }

    async showConfiguration() {
        // Open VSCode settings for this extension
        await vscode.commands.executeCommand('workbench.action.openSettings', 'voiceCopilot');
    }

    async testConnection() {
        const config = vscode.workspace.getConfiguration('voiceCopilot');

        vscode.window.showInformationMessage('🔍 Testing connections...');

        // Test ASR connection
        try {
            const asrUrl = config.get('asr.url', 'http://localhost:8000/transcribe');
            const asrHealthUrl = asrUrl.replace('/transcribe', '/health');

            await axios.get(asrHealthUrl, { timeout: 5000 });
            vscode.window.showInformationMessage('✅ ASR service connected');
        } catch (error) {
            vscode.window.showWarningMessage(`❌ ASR service not reachable: ${error.message}`);
        }

        // Test MCP connection if enabled
        if (config.get('mcp.enabled', false)) {
            try {
                const mcpUrl = config.get('mcp.url', 'http://localhost:3000/mcp');

                const testRequest = {
                    jsonrpc: '2.0',
                    id: Date.now(),
                    method: 'ping',
                    params: {}
                };

                await axios.post(mcpUrl, testRequest, {
                    headers: { 'Content-Type': 'application/json' },
                    timeout: 5000
                });

                vscode.window.showInformationMessage('✅ MCP service connected');
            } catch (error) {
                vscode.window.showWarningMessage(`❌ MCP service not reachable: ${error.message}`);
            }
        }
    }
}

class VoiceCopilotProvider implements vscode.TreeDataProvider<VoiceCopilotItem> {
    getTreeItem(element: VoiceCopilotItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: VoiceCopilotItem): Thenable<VoiceCopilotItem[]> {
        if (!element) {
            // Root level items
            return Promise.resolve([
                new VoiceCopilotItem('Start Recording', 'Click to start voice recording', vscode.TreeItemCollapsibleState.None, {
                    command: 'voiceCopilot.startRecording',
                    title: 'Start Recording'
                }),
                new VoiceCopilotItem('Configure', 'Configure voice settings', vscode.TreeItemCollapsibleState.None, {
                    command: 'voiceCopilot.configure',
                    title: 'Configure'
                }),
                new VoiceCopilotItem('Test Connection', 'Test ASR and MCP connections', vscode.TreeItemCollapsibleState.None, {
                    command: 'voiceCopilot.testConnection',
                    title: 'Test Connection'
                })
            ]);
        }
        return Promise.resolve([]);
    }
}

class VoiceCopilotItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly tooltip: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly command?: vscode.Command
    ) {
        super(label, collapsibleState);
        this.tooltip = tooltip;
        this.command = command;
    }

    iconPath = {
        light: path.join(__filename, '..', '..', 'resources', 'mic-light.svg'),
        dark: path.join(__filename, '..', '..', 'resources', 'mic-dark.svg')
    };
}