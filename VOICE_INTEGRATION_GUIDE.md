# 🎤 Voice Copilot Integration - Complete Guide

## Yes, you CAN add a microphone button to Copilot! Here's how:

I've created **4 different approaches** to integrate voice input with GitHub Copilot, each with different trade-offs and use cases.

---

## 🚀 **Quick Start (Recommended)**

### Option 1: Browser Extension (Easiest)
```bash
# 1. Install the browser extension
# Open Chrome/Edge → chrome://extensions/ → Load unpacked → select browser-extension/

# 2. Configure your ASR service
# Click extension icon → Set ASR URL to: http://localhost:8000/transcribe

# 3. Start your TTS AI Pipeline
make k8s-setup

# 4. Use voice in Copilot!
# Open Copilot Chat → Click 🎤 button → Speak → Press Enter
```

---

## 📋 **All Integration Methods**

### 1. 🖥️ **Desktop Overlay** (`voice_copilot_overlay.py`)
- **What it does**: Floating microphone button over any window
- **Best for**: Users who want voice input anywhere
- **Setup**: `pip install -r requirements_overlay.txt && python voice_copilot_overlay.py`
- **Usage**: Click button → Speak → Switch to Copilot → Paste

### 2. 🌐 **Web Widget** (`voice_copilot_widget.html`)
- **What it does**: Standalone web page with voice interface
- **Best for**: Quick testing and demos
- **Setup**: Open in browser, configure ASR URL
- **Usage**: Click microphone → Speak → Copy transcription → Paste in Copilot

### 3. 🔌 **Browser Extension** (`browser-extension/`)
- **What it does**: Integrates directly into Copilot's interface
- **Best for**: Seamless Copilot integration
- **Setup**: Load as unpacked extension in Chrome/Edge
- **Usage**: Voice button appears next to Copilot's input field

### 4. 🐍 **Python API** (`demo_voice_copilot.py`)
- **What it does**: Programmatic voice-to-Copilot integration
- **Best for**: Developers building custom integrations
- **Setup**: `python demo_voice_copilot.py`
- **Usage**: Interactive command-line demo

---

## ⚙️ **Configuration**

### Required: Start Your TTS AI Pipeline
```bash
# Make sure your ASR service is running
make k8s-setup
make k8s-status  # Check if running
```

### Environment Variables
```bash
# Set these for all methods
export ASR_URL="http://localhost:8000/transcribe"
export MCP_ENABLED="true"  # Optional, for direct Copilot integration
```

---

## 🎯 **Which Method Should You Use?**

| Method | Difficulty | Integration | Best For |
|--------|------------|-------------|----------|
| Browser Extension | ⭐⭐⭐ | Seamless | Most users |
| Desktop Overlay | ⭐⭐⭐⭐ | Floating | Power users |
| Web Widget | ⭐⭐ | Standalone | Testing/Demos |
| Python API | ⭐⭐⭐⭐⭐ | Custom | Developers |

### **My Recommendation**: Start with the **Browser Extension** - it's the most seamless experience!

---

## 🔧 **Troubleshooting**

### "Microphone not working"
- ✅ Allow microphone permissions in browser
- ✅ Make sure you're on HTTPS (required for mic access)
- ✅ Check browser console for errors

### "ASR service not found"
- ✅ Verify pipeline is running: `make k8s-status`
- ✅ Check ASR URL configuration
- ✅ Test service: `curl http://localhost:8000/health`

### "Extension not showing"
- ✅ Refresh the Copilot page
- ✅ Check if you're on github.com/copilot
- ✅ Verify extension is enabled

### "Hotkeys not working"
- ✅ Make sure target window has focus
- ✅ Check for conflicts with other apps
- ✅ Try different hotkey combinations

---

## 🎨 **Customization**

### Change Hotkeys
```javascript
// In browser extension content.js
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.altKey && e.key === 'V') {  // Change to Ctrl+Alt+V
        // ... trigger recording
    }
});
```

### Customize Appearance
```css
/* In voice_copilot_widget.html */
.voice-button {
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}
```

### Add Voice Commands
```python
# In mcp_client.py
def detect_voice_commands(transcription):
    commands = {
        "explain this code": "Please explain the following code:",
        "debug this": "Please help debug this code:",
        "refactor this": "Please refactor this code:"
    }
    # ... command detection logic
```

---

## 🚀 **Advanced Features**

### Direct MCP Integration
```python
# Send directly to Copilot without clipboard
from voice_ai_pipeline.mcp_client import MCPClient

client = MCPClient()
response = client.send_to_copilot("Help me write a Python function")
print(response['result'])
```

### Custom Voice Commands
```python
# Add voice-activated commands
voice_commands = {
    "open terminal": lambda: os.system("gnome-terminal"),
    "new file": lambda: create_new_file(),
    "search": lambda query: search_codebase(query)
}
```

### Multi-Language Support
```python
# Auto-detect language and respond accordingly
detected_lang = detect_language(transcription)
if detected_lang == 'es':
    prompt = f"Por favor responde en español: {transcription}"
```

---

## 📚 **Next Steps**

1. **Try the Browser Extension** - Most seamless experience
2. **Customize the hotkeys** - Make it fit your workflow
3. **Add voice commands** - Create shortcuts for common tasks
4. **Integrate with your editor** - Extend beyond just Copilot

---

## 🤝 **Contributing**

Found a bug or want to add a feature? The code is fully open-source:

- **Browser Extension**: `browser-extension/` folder
- **Desktop Overlay**: `voice_copilot_overlay.py`
- **Web Widget**: `voice_copilot_widget.html`
- **MCP Client**: `voice_ai_pipeline/mcp_client.py`

Feel free to submit issues, feature requests, or pull requests!

---

**🎉 Happy voice coding with Copilot!**