#!/usr/bin/env python3
"""
Microphone Recording Component for TTS AI Pipeline

This component provides microphone recording capabilities for testing
the ASR (Automatic Speech Recognition) functionality of the TTS AI Pipeline.

Features:
- Record audio from available microphones
- Save recordings in WAV format
- Test ASR transcription with recorded audio
- List available audio devices
- Real-time audio level monitoring

Usage:
    python -m tts_ai_pipeline.microphone

Requirements:
    - pyaudio (optional, for microphone recording)
      Install system dependencies first:
      Ubuntu/Debian: sudo apt-get install portaudio19-dev
      macOS: brew install portaudio
      Windows: (usually works with pip install)
    - numpy
    - requests

Note: If PyAudio is not available, the component will provide helpful error messages.
"""

try:
    import pyaudio  # type: ignore
    PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None  # type: ignore
    PYAUDIO_AVAILABLE = False

import numpy as np
import time
import os
import sys
import tempfile
from typing import Optional, List, Tuple
import requests
import json

import pyaudio
import wave
import numpy as np
import time
import os
import sys
import tempfile
from typing import Optional, List, Tuple
import requests
import json


class MicrophoneRecorder:
    """Microphone recording component for ASR testing."""

    def __init__(self, asr_url: str = "http://localhost:8000"):
        if not PYAUDIO_AVAILABLE:
            raise ImportError("PyAudio is not available. Please install it with: pip install pyaudio")
        
        self.asr_url = asr_url
        self.audio = pyaudio.PyAudio()  # type: ignore
        self.stream: Optional[pyaudio.Stream] = None  # type: ignore
        self.frames = []
        self.is_recording = False

        # Audio parameters
        self.chunk = 1024
        self.format = pyaudio.paInt16  # type: ignore
        self.channels = 1
        self.rate = 16000  # 16kHz for better ASR performance

    def list_devices(self) -> List[Tuple[int, str]]:
        """List all available audio input devices."""
        devices = []
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            max_input = device_info.get('maxInputChannels', 0)
            if isinstance(max_input, (int, float)) and max_input > 0:
                devices.append((i, device_info.get('name', f'Device {i}')))
        return devices

    def get_default_input_device(self) -> Optional[int]:
        """Get the default input device index."""
        try:
            default_device = self.audio.get_default_input_device_info()
            device_index = default_device.get('index')
            if isinstance(device_index, int):
                return device_index
            return None
        except Exception:
            return None

    def start_recording(self, device_index: Optional[int] = None, duration: Optional[float] = None) -> bool:
        """
        Start recording from microphone.

        Args:
            device_index: Audio device index (None for default)
            duration: Recording duration in seconds (None for manual stop)

        Returns:
            True if recording started successfully
        """
        try:
            if device_index is None:
                device_index = self.get_default_input_device()
                if device_index is None:
                    print("❌ No default input device found")
                    return False

            # Validate device
            device_info = self.audio.get_device_info_by_index(device_index)
            if device_info.get('maxInputChannels') == 0:
                print(f"❌ Device {device_index} is not an input device")
                return False

            print(f"🎤 Starting recording from: {device_info.get('name')}")
            print("   Press Ctrl+C to stop recording" if duration is None else f"   Recording for {duration} seconds...")

            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )

            self.frames = []
            self.is_recording = True

            if duration:
                # Record for specified duration
                for _ in range(int(self.rate / self.chunk * duration)):
                    if not self.is_recording:
                        break
                    data = self.stream.read(self.chunk)
                    self.frames.append(data)
                self.stop_recording()
            else:
                # Record until manually stopped
                try:
                    while self.is_recording:
                        data = self.stream.read(self.chunk)
                        self.frames.append(data)
                        # Simple audio level monitoring
                        audio_data = np.frombuffer(data, dtype=np.int16)
                        rms = np.sqrt(np.mean(audio_data**2))
                        if rms > 100:  # Basic voice activity detection
                            print(".", end="", flush=True)
                except KeyboardInterrupt:
                    print("\n🛑 Recording stopped by user")
                    self.stop_recording()

            return True

        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            return False

    def stop_recording(self):
        """Stop the current recording."""
        if self.stream and self.is_recording:
            self.is_recording = False
            self.stream.stop_stream()
            self.stream.close()
            print("✅ Recording stopped")

    def save_recording(self, filename: str) -> bool:
        """
        Save the recorded audio to a WAV file.

        Args:
            filename: Output filename

        Returns:
            True if saved successfully
        """
        if not self.frames:
            print("❌ No audio data to save")
            return False

        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))

            file_size = os.path.getsize(filename)
            print(f"💾 Audio saved to {filename} ({file_size} bytes)")
            return True

        except Exception as e:
            print(f"❌ Failed to save recording: {e}")
            return False

    def transcribe_recording(self, audio_file: str) -> Optional[str]:
        """
        Transcribe recorded audio using ASR service.

        Args:
            audio_file: Path to audio file

        Returns:
            Transcribed text or None if failed
        """
        try:
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.asr_url}/transcribe",
                    files=files,
                    timeout=30
                )

            if response.status_code == 200:
                data = response.json()
                text = data.get('text', '').strip()
                print(f"📝 Transcription: '{text}'")
                return text
            else:
                print(f"❌ ASR request failed: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return None

    def record_and_transcribe(self, device_index: Optional[int] = None,
                            duration: float = 5.0) -> Optional[str]:
        """
        Record audio and immediately transcribe it.

        Args:
            device_index: Audio device index
            duration: Recording duration in seconds

        Returns:
            Transcribed text or None if failed
        """
        # Record audio
        if not self.start_recording(device_index, duration):
            return None

        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            if not self.save_recording(temp_filename):
                return None

            # Transcribe
            return self.transcribe_recording(temp_filename)

        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def cleanup(self):
        """Clean up resources."""
        if self.stream:
            self.stop_recording()
        self.audio.terminate()


def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Microphone Recording Component for TTS AI Pipeline")
    parser.add_argument('--list-devices', action='store_true', help='List available audio devices')
    parser.add_argument('--device', type=int, help='Audio device index')
    parser.add_argument('--duration', type=float, default=5.0, help='Recording duration in seconds')
    parser.add_argument('--asr-url', default='http://localhost:8000', help='ASR service URL')
    parser.add_argument('--output', help='Output WAV file path')
    parser.add_argument('--test', action='store_true', help='Record and transcribe test')

    args = parser.parse_args()

    # Check PyAudio availability
    if not PYAUDIO_AVAILABLE:
        print("❌ PyAudio is not available.")
        print("📦 To install PyAudio:")
        print("   Ubuntu/Debian: sudo apt-get install portaudio19-dev && pip install pyaudio")
        print("   macOS: brew install portaudio && pip install pyaudio")
        print("   Windows: pip install pyaudio")
        print("\nAlternatively, you can install the system package:")
        print("   Ubuntu/Debian: sudo apt-get install python3-pyaudio")
        return 1

    recorder = None
    try:
        recorder = MicrophoneRecorder(args.asr_url)

        if args.list_devices:
            devices = recorder.list_devices()
            if devices:
                print("🎤 Available audio input devices:")
                for idx, name in devices:
                    print(f"  {idx}: {name}")
            else:
                print("❌ No audio input devices found")
            return

        if args.test:
            print("🧪 Recording and transcribing test...")
            text = recorder.record_and_transcribe(args.device, args.duration)
            if text:
                print(f"✅ Test successful: '{text}'")
            else:
                print("❌ Test failed")
            return

        if args.output:
            print(f"🎤 Recording {args.duration} seconds to {args.output}...")
            if recorder.start_recording(args.device, args.duration):
                recorder.save_recording(args.output)
                print("✅ Recording saved")
            else:
                print("❌ Recording failed")
            return

        # Interactive mode
        devices = recorder.list_devices()
        if not devices:
            print("❌ No audio input devices found")
            return

        print("🎤 Available devices:")
        for idx, name in devices:
            print(f"  {idx}: {name}")

        default_device = recorder.get_default_input_device()
        device_choice = input(f"Enter device index (default {default_device}): ").strip()
        device_index = int(device_choice) if device_choice else default_device

        duration_choice = input("Enter recording duration in seconds (default 5): ").strip()
        duration = float(duration_choice) if duration_choice else 5.0

        print(f"🎤 Recording from device {device_index} for {duration} seconds...")
        text = recorder.record_and_transcribe(device_index, duration)

        if text:
            print(f"📝 Final transcription: '{text}'")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if recorder is not None:
            recorder.cleanup()


if __name__ == "__main__":
    main()
