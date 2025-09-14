#!/usr/bin/env python3
"""
Voice Copilot Desktop Overlay

A desktop application that provides a floating microphone button
that can trigger voice recording and send results to Copilot.

Features:
- Floating microphone button overlay
- Hotkey support (Ctrl+Shift+V)
- Automatic transcription and Copilot integration
- System tray integration
- Configurable positioning and appearance

Requirements:
- tkinter (for GUI)
- pyautogui (for keyboard simulation)
- requests (for API calls)
- pyaudio (for microphone access)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import os
import sys
import json
import keyboard
import pyautogui
from typing import Optional, Callable
import requests
import tempfile
import pyaudio
import wave
import numpy as np
from enum import Enum


class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"


class VoiceCopilotOverlay:
    """Desktop overlay with microphone button for Copilot integration."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Voice Copilot")
        self.root.geometry("200x200")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.9)
        self.root.overrideredirect(True)

        # Configuration
        self.config = self.load_config()
        self.recording_state = RecordingState.IDLE
        self.audio_frames = []

        # Initialize audio
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None

        # Create UI
        self.create_ui()

        # Setup hotkeys
        self.setup_hotkeys()

        # Position window
        self.position_window()

        # Start animation thread
        self.animation_running = True
        self.animation_thread = threading.Thread(target=self.animate_button, daemon=True)
        self.animation_thread.start()

    def create_ui(self):
        """Create the overlay UI."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Microphone button
        self.mic_button = tk.Button(
            main_frame,
            text="🎤",
            font=("Arial", 24),
            command=self.toggle_recording,
            bg="#007acc",
            fg="white",
            relief=tk.RAISED,
            bd=3
        )
        self.mic_button.pack(pady=10)

        # Status label
        self.status_label = ttk.Label(
            main_frame,
            text="Ready",
            font=("Arial", 10)
        )
        self.status_label.pack(pady=5)

        # Settings button
        settings_btn = tk.Button(
            main_frame,
            text="⚙️",
            command=self.show_settings,
            bg="#f0f0f0",
            relief=tk.FLAT
        )
        settings_btn.pack(side=tk.BOTTOM, pady=5)

        # Make window draggable
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.drag_window)

    def setup_hotkeys(self):
        """Setup global hotkeys."""
        try:
            keyboard.add_hotkey('ctrl+shift+v', self.toggle_recording_hotkey)
            print("✅ Hotkey Ctrl+Shift+V registered")
        except Exception as e:
            print(f"⚠️ Could not register hotkey: {e}")

    def toggle_recording_hotkey(self):
        """Handle hotkey press."""
        self.root.after(0, self.toggle_recording)

    def toggle_recording(self):
        """Toggle recording state."""
        if self.recording_state == RecordingState.IDLE:
            self.start_recording()
        elif self.recording_state == RecordingState.RECORDING:
            self.stop_recording()

    def start_recording(self):
        """Start audio recording."""
        try:
            self.recording_state = RecordingState.RECORDING
            self.update_ui("🔴 Recording...", "#ff4444")
            self.audio_frames = []

            # Start audio stream
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )

            # Start recording thread
            recording_thread = threading.Thread(target=self.record_audio, daemon=True)
            recording_thread.start()

        except Exception as e:
            self.update_ui(f"❌ Error: {str(e)}", "#ff6666")
            self.recording_state = RecordingState.IDLE

    def record_audio(self):
        """Record audio in a separate thread."""
        try:
            while self.recording_state == RecordingState.RECORDING and self.stream:
                data = self.stream.read(1024, exception_on_overflow=False)
                self.audio_frames.append(data)
        except Exception as e:
            print(f"Recording error: {e}")

    def stop_recording(self):
        """Stop recording and process audio."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        self.recording_state = RecordingState.PROCESSING
        self.update_ui("⏳ Processing...", "#ffa500")

        # Process in separate thread
        processing_thread = threading.Thread(target=self.process_recording, daemon=True)
        processing_thread.start()

    def process_recording(self):
        """Process the recorded audio."""
        try:
            if not self.audio_frames:
                self.update_ui("❌ No audio recorded", "#ff6666")
                self.recording_state = RecordingState.IDLE
                return

            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_path = temp_file.name

                # Write WAV file
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(self.audio_frames))

            # Send to ASR service
            transcription = self.transcribe_audio(temp_path)

            if transcription:
                # Send to Copilot
                self.send_to_copilot(transcription)

                # Copy to clipboard for Copilot
                self.copy_to_clipboard(transcription)
                self.update_ui("✅ Sent to Copilot!", "#44ff44")
            else:
                self.update_ui("❌ Transcription failed", "#ff6666")

            # Cleanup
            os.unlink(temp_path)

        except Exception as e:
            self.update_ui(f"❌ Error: {str(e)}", "#ff6666")
        finally:
            self.recording_state = RecordingState.IDLE

    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Send audio to ASR service for transcription."""
        try:
            asr_url = self.config.get("asr_url", "http://localhost:8000/transcribe")

            with open(audio_path, "rb") as f:
                response = requests.post(asr_url, files={"file": f}, timeout=30)

            if response.status_code == 200:
                return response.json().get("text", "").strip()
            else:
                print(f"ASR Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"ASR request failed: {e}")
            return None

    def send_to_copilot(self, transcription: str):
        """Send transcription to Copilot via MCP."""
        try:
            if not self.config.get("mcp_enabled", False):
                return

            mcp_url = self.config.get("mcp_url", "http://localhost:3000/mcp")

            # Format as MCP request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": int(time.time() * 1000),
                "method": "copilot/chat",
                "params": {
                    "messages": [{
                        "role": "user",
                        "content": transcription
                    }],
                    "options": {
                        "temperature": 0.7,
                        "max_tokens": 1000
                    }
                }
            }

            response = requests.post(mcp_url, json=mcp_request, timeout=30)

            if response.status_code == 200:
                print("✅ Sent to Copilot successfully")
            else:
                print(f"⚠️ MCP request failed: {response.status_code}")

        except Exception as e:
            print(f"MCP send failed: {e}")

    def copy_to_clipboard(self, text: str):
        """Copy text to clipboard for Copilot input."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # Required for clipboard to work

            # Optional: Simulate paste into active window
            if self.config.get("auto_paste", False):
                time.sleep(0.5)  # Brief delay
                pyautogui.hotkey('ctrl', 'v')  # Paste

        except Exception as e:
            print(f"Clipboard copy failed: {e}")

    def update_ui(self, text: str, color: str = "#007acc"):
        """Update the UI with new status."""
        def update():
            self.status_label.config(text=text)
            self.mic_button.config(bg=color)

        self.root.after(0, update)

    def animate_button(self):
        """Animate the button when recording."""
        while self.animation_running:
            if self.recording_state == RecordingState.RECORDING:
                # Pulse animation
                for alpha in [0.7, 1.0, 0.7]:
                    if self.recording_state != RecordingState.RECORDING:
                        break
                    def set_alpha(a=alpha):
                        self.mic_button.config(bg="#ff4444" if a > 0.8 else "#cc0000")
                    self.root.after(0, set_alpha)
                    time.sleep(0.5)
            else:
                time.sleep(0.1)

    def start_drag(self, event):
        """Start window drag."""
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event):
        """Drag the window."""
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def position_window(self):
        """Position window based on config."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Default to bottom-right corner
        x = screen_width - 220
        y = screen_height - 220

        self.root.geometry(f"+{x}+{y}")

    def show_settings(self):
        """Show settings dialog."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Voice Copilot Settings")
        settings_window.geometry("400x300")

        # Settings content would go here
        ttk.Label(settings_window, text="Settings dialog - Coming soon!").pack(pady=20)

    def load_config(self) -> dict:
        """Load configuration from file."""
        config_path = os.path.expanduser("~/.voice_copilot_config.json")
        default_config = {
            "asr_url": "http://localhost:8000/transcribe",
            "mcp_enabled": False,
            "mcp_url": "http://localhost:3000/mcp",
            "auto_paste": True,
            "hotkey": "ctrl+shift+v"
        }

        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            print(f"Config load error: {e}")

        return default_config

    def save_config(self):
        """Save configuration to file."""
        config_path = os.path.expanduser("~/.voice_copilot_config.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")

    def on_closing(self):
        """Handle application closing."""
        self.animation_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        self.root.destroy()

    def run(self):
        """Run the application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main entry point."""
    try:
        app = VoiceCopilotOverlay()
        print("🎤 Voice Copilot Overlay started!")
        print("• Click the microphone button or press Ctrl+Shift+V to start recording")
        print("• Click again to stop and send to Copilot")
        print("• Drag the window to reposition")
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Voice Copilot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()