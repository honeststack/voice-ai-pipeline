#!/usr/bin/env python3
"""
Voice Copilot Demo Script

This script demonstrates how to integrate voice input with Copilot
using the TTS AI Pipeline and MCP client.

Usage:
    python demo_voice_copilot.py
"""

import os
import sys
import time
import json
from typing import Optional

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from voice_ai_pipeline.mcp_client import MCPClient, create_copilot_prompt
    from voice_ai_pipeline.microphone import MicrophoneRecorder
    MCP_AVAILABLE = True
except ImportError as e:
    print(f"❌ Required modules not available: {e}")
    print("Please make sure the TTS AI Pipeline is properly installed.")
    MCP_AVAILABLE = False
    MCPClient = None
    MicrophoneRecorder = None


class VoiceCopilotDemo:
    """Demo class showing voice-to-Copilot integration."""

    def __init__(self):
        if not MCP_AVAILABLE or MCPClient is None or MicrophoneRecorder is None:
            raise ImportError("MCP components not available")

        self.mcp_client = MCPClient()
        self.microphone = MicrophoneRecorder()
        self.is_running = False

    def run_interactive_demo(self):
        """Run an interactive voice-to-Copilot demo."""
        print("🎤 Voice Copilot Demo")
        print("=" * 50)
        print("This demo will:")
        print("1. Record your voice")
        print("2. Transcribe it using ASR")
        print("3. Send it to Copilot via MCP")
        print("4. Display the response")
        print()
        print("Commands:")
        print("• 'record' or 'r' - Start recording")
        print("• 'stop' or 's' - Stop recording")
        print("• 'quit' or 'q' - Exit demo")
        print()

        self.is_running = True

        while self.is_running:
            try:
                command = input("🎤 Voice Copilot > ").strip().lower()

                if command in ['quit', 'q', 'exit']:
                    break
                elif command in ['record', 'r']:
                    self.record_and_process()
                elif command in ['stop', 's']:
                    print("ℹ️  Recording stopped")
                elif command == 'help':
                    self.show_help()
                else:
                    print(f"❓ Unknown command: {command}")
                    print("Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n👋 Demo interrupted")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

        print("👋 Demo finished!")

    def record_and_process(self):
        """Record audio and process it through the pipeline."""
        print("🎤 Starting recording... (Press Ctrl+C to stop)")

        try:
            # Start recording
            devices = self.microphone.list_devices()
            if not devices:
                print("❌ No microphone devices found")
                return

            print(f"📱 Found {len(devices)} audio device(s)")
            for i, (idx, name) in enumerate(devices):
                print(f"  {i+1}. {name}")

            # Use default device or first available
            device_index = self.microphone.get_default_input_device()
            if device_index is None and devices:
                device_index = devices[0][0]

            if device_index is None:
                print("❌ No suitable audio device found")
                return

            # Start recording for 5 seconds (you can make this configurable)
            print("🎤 Recording for 5 seconds...")
            self.microphone.start_recording(device_index, duration=5)

            # Wait for recording to complete
            time.sleep(6)  # A bit longer than recording duration

            # Process the recording
            self.process_recording()

        except Exception as e:
            print(f"❌ Recording failed: {e}")

    def process_recording(self):
        """Process the recorded audio through ASR and MCP."""
        try:
            print("⏳ Processing recording...")

            # Get the recorded audio data
            if not hasattr(self.microphone, 'frames') or not self.microphone.frames:
                print("❌ No audio data recorded")
                return

            # Save to temporary WAV file
            import tempfile
            import wave

            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_path = temp_file.name

                # Write WAV file
                with wave.open(temp_path, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(self.microphone.frames))

            # Transcribe using ASR service
            transcription = self.transcribe_audio(temp_path)

            if transcription:
                print(f"📝 Transcription: {transcription}")

                # Send to Copilot
                self.send_to_copilot_demo(transcription)
            else:
                print("❌ Transcription failed")

            # Cleanup
            os.unlink(temp_path)

        except Exception as e:
            print(f"❌ Processing failed: {e}")

    def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Send audio to ASR service for transcription."""
        try:
            import requests

            asr_url = os.getenv("ASR_URL", "http://localhost:8000/transcribe")

            with open(audio_path, "rb") as f:
                response = requests.post(asr_url, files={"file": f}, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result.get("text", "").strip()
            else:
                print(f"❌ ASR Error: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ ASR request failed: {e}")
            return None

    def send_to_copilot_demo(self, transcription: str):
        """Send transcription to Copilot and display response."""
        print("🤖 Sending to Copilot...")

        # Create a prompt
        prompt = self.mcp_client.create_prompt_from_transcription(transcription)
        print(f"📤 Prompt: {prompt.text}")

        # In a real implementation, you would send this to Copilot
        # For demo purposes, we'll simulate a response
        simulated_response = self.simulate_copilot_response(transcription)

        print("📥 Copilot Response:")
        print(f"   {simulated_response}")
        print()

    def simulate_copilot_response(self, transcription: str) -> str:
        """Simulate a Copilot response for demo purposes."""
        # This is just for demonstration
        # In a real implementation, you would use the MCP client to get actual responses

        responses = {
            "hello": "Hello! How can I help you with your coding today?",
            "how are you": "I'm doing well, thank you for asking! I'm here to help you with any programming questions or tasks you might have.",
            "what is python": "Python is a high-level, interpreted programming language known for its simplicity and readability. It's widely used for web development, data science, machine learning, and automation.",
            "help": "I'd be happy to help! You can ask me about programming concepts, debugging code, writing functions, or any other development-related questions.",
        }

        # Simple keyword matching
        transcription_lower = transcription.lower()

        for keyword, response in responses.items():
            if keyword in transcription_lower:
                return response

        # Default response
        return f"I understand you said: '{transcription}'. That's an interesting question! Could you provide more details about what you'd like help with?"

    def show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("• record/r - Start voice recording")
        print("• stop/s - Stop current recording")
        print("• help - Show this help message")
        print("• quit/q/exit - Exit the demo")
        print()

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self.microphone, 'audio'):
            self.microphone.audio.terminate()


def main():
    """Main entry point."""
    if not MCP_AVAILABLE:
        print("❌ This demo requires the TTS AI Pipeline MCP components.")
        print("Please make sure the pipeline is properly installed and configured.")
        return 1

    try:
        demo = VoiceCopilotDemo()
        demo.run_interactive_demo()
        demo.cleanup()
        return 0
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())