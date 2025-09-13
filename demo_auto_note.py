#!/usr/bin/env python3
"""
Demo script for the Auto-Note feature

This script demonstrates how to use the auto-note functionality
to transcribe audio, summarize content, and create OneNote entries.

Usage:
    python demo_auto_note.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tts_ai_pipeline.microphone import MicrophoneRecorder, PYAUDIO_AVAILABLE
from tts_ai_pipeline.summarizer import TextSummarizer, TRANSFORMERS_AVAILABLE
from tts_ai_pipeline.onenote_manager import OneNoteManager, MSGRAPH_AVAILABLE
from tts_ai_pipeline.auto_note import AutoNoteProcessor


def demo_basic_components():
    """Demonstrate individual components."""
    print("🎭 TTS AI Pipeline - Auto-Note Demo")
    print("=" * 50)

    print("\n📦 Component Status:")
    print(f"   Microphone: {'✅ Available' if PYAUDIO_AVAILABLE else '❌ Not available'}")
    print(f"   Summarizer: {'✅ Available' if TRANSFORMERS_AVAILABLE else '❌ Not available'}")
    print(f"   OneNote: {'✅ Available' if MSGRAPH_AVAILABLE else '❌ Not available'}")

    # Demo summarization
    if TRANSFORMERS_AVAILABLE:
        print("\n🤖 Testing Summarization:")
        try:
            summarizer = TextSummarizer()
            sample_text = """
            The TTS AI Pipeline is a comprehensive system for speech processing.
            It includes automatic speech recognition using OpenAI's Whisper models,
            text-to-speech synthesis using Coqui TTS, and a web interface built with Gradio.
            The system is containerized using Docker and orchestrated with Kubernetes,
            making it suitable for both development and production deployments.
            """

            summary = summarizer.summarize(sample_text)
            print(f"   Original: {sample_text[:100]}...")
            print(f"   Summary: {summary}")

        except Exception as e:
            print(f"   ❌ Summarization failed: {e}")

    # Demo microphone (if available)
    if PYAUDIO_AVAILABLE:
        print("\n🎤 Testing Microphone:")
        try:
            recorder = MicrophoneRecorder()
            devices = recorder.list_devices()

            if devices:
                print(f"   Found {len(devices)} audio device(s):")
                for idx, name in devices:
                    print(f"     {idx}: {name}")
            else:
                print("   No audio devices found")

            recorder.cleanup()

        except Exception as e:
            print(f"   ❌ Microphone test failed: {e}")

    # Demo OneNote (if configured)
    if MSGRAPH_AVAILABLE:
        print("\n📓 Testing OneNote:")
        try:
            # Try to initialize without credentials (will show auth requirements)
            manager = OneNoteManager(client_id=None)
            print("   OneNote manager initialized (authentication required for full functionality)")

        except Exception as e:
            print(f"   OneNote test: {e}")


def demo_auto_note_processor():
    """Demonstrate the complete auto-note processor."""
    print("\n🔄 Testing Auto-Note Processor:")
    print("-" * 30)

    try:
        # Initialize processor (without OneNote credentials for demo)
        processor = AutoNoteProcessor(
            onenote_client_id=None,
            onenote_tenant_id=None,
            onenote_client_secret=None
        )

        print("✅ Auto-Note processor initialized successfully")

        # Show component status
        components = []
        if hasattr(processor, 'microphone') and processor.microphone:
            components.append("Microphone")
        if hasattr(processor, 'summarizer') and processor.summarizer:
            components.append("Summarizer")
        if hasattr(processor, 'onenote') and processor.onenote:
            components.append("OneNote")

        if components:
            print(f"   Active components: {', '.join(components)}")
        else:
            print("   No components active (missing dependencies)")

    except Exception as e:
        print(f"❌ Auto-Note processor initialization failed: {e}")


def demo_file_processing():
    """Demonstrate processing an audio file."""
    print("\n🎵 File Processing Demo:")
    print("-" * 25)

    # Create a simple demo (would need actual audio file for real demo)
    print("   Note: This demo requires an actual audio file for full functionality")
    print("   Example usage:")
    print("   python -m tts_ai_pipeline.auto_note --audio-file my_recording.wav")
    print("   python -m tts_ai_pipeline.auto_note --record --duration 10")


def demo_setup_instructions():
    """Show setup instructions."""
    print("\n🔧 Setup Instructions:")
    print("-" * 22)

    print("1. Install dependencies:")
    print("   pip install -r requirements_test.txt")

    print("\n2. For PyAudio (microphone):")
    print("   Ubuntu/Debian: sudo apt-get install portaudio19-dev python3-pyaudio")
    print("   macOS: brew install portaudio && pip install pyaudio")
    print("   Windows: pip install pyaudio")

    print("\n3. For Microsoft OneNote:")
    print("   - Register app in Azure AD: https://portal.azure.com")
    print("   - Add OneNote permissions: Notes.ReadWrite, Notes.ReadWrite.All")
    print("   - Set environment variables:")
    print("     export AZURE_CLIENT_ID='your-client-id'")
    print("     export AZURE_TENANT_ID='your-tenant-id'")
    print("     export AZURE_CLIENT_SECRET='your-client-secret'")

    print("\n4. Usage examples:")
    print("   # Process audio file")
    print("   python -m tts_ai_pipeline.auto_note --audio-file recording.wav")
    print("   ")
    print("   # Record live audio")
    print("   python -m tts_ai_pipeline.auto_note --record --duration 30")
    print("   ")
    print("   # Test components")
    print("   python -m tts_ai_pipeline.microphone --list-devices")
    print("   python -m tts_ai_pipeline.summarizer --text 'Your text here'")


def main():
    """Main demo function."""
    try:
        demo_basic_components()
        demo_auto_note_processor()
        demo_file_processing()
        demo_setup_instructions()

        print("\n🎉 Demo completed!")
        print("\nFor more information, see the Auto-Note section in README.md")

    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
