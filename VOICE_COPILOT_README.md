# Voice Copilot Integration

Add voice input capability to GitHub Copilot Chat using your TTS AI Pipeline.

## 🎯 Overview

This project provides multiple approaches to integrate voice input with GitHub Copilot, allowing you to speak naturally and have your words transcribed and sent to Copilot for AI-powered responses.

## 🔧 Integration Methods

### 1. 🖥️ Desktop Overlay Application
A floating microphone button that appears over any window, including Copilot.

**Features:**
- Floating microphone button overlay
- Global hotkey support (Ctrl+Shift+V)
- Automatic transcription and clipboard integration
- Configurable positioning and appearance

**Setup:**
```bash
# Install dependencies
pip install -r requirements_overlay.txt

# Run the overlay
python voice_copilot_overlay.py
```

**Usage:**
1. The microphone button appears in the bottom-right corner
2. Click it or press Ctrl+Shift+V to start recording
3. Speak your message
4. Click again to stop and process
5. Switch to Copilot and paste (Ctrl+V)

### 2. 🌐 Web Widget
A standalone web page that can be used alongside Copilot.

**Features:**
- Modern, responsive web interface
- Real-time recording with visual feedback
- Automatic clipboard integration
- Settings panel for configuration

**Usage:**
1. Open `voice_copilot_widget.html` in your browser
2. Click the microphone button or press Ctrl+Shift+V
3. Speak your message
4. The transcription is automatically copied to clipboard
5. Switch to Copilot and paste

### 3. 🔌 Browser Extension (Recommended)
A browser extension that integrates directly into Copilot's web interface.

**Features:**
- Seamless integration with Copilot Chat
- Voice button appears next to the chat input
- Automatic transcription insertion
- Global keyboard shortcuts
- Settings management

**Installation:**
1. Open Chrome/Edge and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `browser-extension` folder
4. The extension will be installed and active

**Usage:**
1. Open GitHub Copilot Chat
2. Look for the microphone button (🎤) next to the input field
3. Click it or press Ctrl+Shift+V to start recording
4. Speak your message
5. The transcription appears directly in the chat input
6. Press Enter to send to Copilot

## ⚙️ Configuration

### Environment Variables
Set these in your environment or in the respective configuration files:

```bash
# ASR Service
ASR_URL=http://localhost:8000/transcribe

# MCP Integration (optional)
MCP_ENABLED=true
COPILOT_MCP_URL=http://localhost:3000/mcp

# Overlay settings
AUTO_PASTE=true
```

### Browser Extension Settings
Access the extension settings by:
1. Clicking the extension icon in the browser toolbar
2. Configuring ASR service URL and MCP settings
3. Testing the connection

## 🚀 Getting Started

### Prerequisites
1. **TTS AI Pipeline**: Make sure your ASR service is running
   ```bash
   # Start your TTS AI Pipeline
   make k8s-setup
   ```

2. **Browser Permissions**: For the web widget and browser extension
   - Allow microphone access when prompted
   - Grant clipboard permissions

### Quick Start
1. **Choose your integration method** above
2. **Configure the ASR service URL** to point to your running pipeline
3. **Test the connection** using the built-in test features
4. **Start using voice input** with Copilot!

## 🎨 Customization

### Desktop Overlay
- Modify `voice_copilot_overlay.py` for custom appearance
- Adjust positioning, colors, and hotkeys
- Add system tray integration

### Web Widget
- Edit `voice_copilot_widget.html` for custom styling
- Modify the CSS for different themes
- Add additional features like voice commands

### Browser Extension
- Customize the button appearance in `content.js`
- Modify keyboard shortcuts
- Add additional Copilot integrations

## 🔧 Troubleshooting

### Common Issues

**Microphone not working:**
- Check browser permissions
- Ensure HTTPS (required for microphone access)
- Try refreshing the page

**ASR service connection failed:**
- Verify your TTS AI Pipeline is running
- Check the ASR_URL configuration
- Test the service directly: `curl http://localhost:8000/health`

**Extension not appearing:**
- Check if you're on a GitHub Copilot page
- Try refreshing the page
- Check browser console for errors

**Hotkeys not working:**
- Make sure the target application has focus
- Check for conflicts with other applications
- Try different hotkey combinations

### Debug Mode
Enable debug logging by opening the browser console and looking for messages prefixed with 🎤.

## 📚 API Reference

### ASR Service
```
POST /transcribe
Content-Type: multipart/form-data
Body: file=audio.wav

Response: {"text": "transcribed text"}
```

### MCP Integration (Optional)
```
POST /mcp
Content-Type: application/json
Body: {
  "jsonrpc": "2.0",
  "method": "copilot/chat",
  "params": {
    "messages": [{"role": "user", "content": "your text"}]
  }
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to:

- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

## 📄 License

This project is part of the TTS AI Pipeline and follows the same MIT license.

## 🙏 Acknowledgments

- Built on top of the TTS AI Pipeline
- Uses Web Audio API for recording
- Integrates with GitHub Copilot via MCP protocol
- Inspired by voice-first AI interactions