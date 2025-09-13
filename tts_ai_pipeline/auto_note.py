#!/usr/bin/env python3
"""
Auto-Note Component for TTS AI Pipeline

This component automatically transcribes audio, summarizes the transcription,
and creates notes in Microsoft OneNote.

Features:
- End-to-end audio processing pipeline
- Automatic transcription using ASR service
- Intelligent text summarization
- OneNote integration for note creation
- Configurable processing parameters
- Error handling and recovery

Usage:
    python -m tts_ai_pipeline.auto_note --audio-file recording.wav
    python -m tts_ai_pipeline.auto_note --record --duration 10

Requirements:
    - All dependencies from microphone, summarizer, and onenote_manager components
    - Microsoft Azure app registration
    - ASR service running (optional, falls back to local processing)
"""

import os
import sys
import time
import tempfile
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

# Import our components
from .microphone import MicrophoneRecorder, PYAUDIO_AVAILABLE
from .summarizer import TextSummarizer, TRANSFORMERS_AVAILABLE
from .onenote_manager import OneNoteManager, MSGRAPH_AVAILABLE
from .local_notes import LocalNoteManager


class AutoNoteProcessor:
    """Main component for automatic note creation from audio."""

    def __init__(self, asr_url: str = "http://localhost:8000",
                 onenote_client_id: Optional[str] = None,
                 onenote_tenant_id: Optional[str] = None,
                 onenote_client_secret: Optional[str] = None,
                 summarizer_model: str = "medium",
                 note_storage: str = "auto"):
        """
        Initialize the auto-note processor.

        Args:
            asr_url: URL of the ASR service
            onenote_client_id: Azure app client ID for OneNote
            onenote_tenant_id: Azure tenant ID
            onenote_client_secret: Azure app client secret
            summarizer_model: Size of summarization model ('small', 'medium', 'large')
            note_storage: Note storage method ('auto', 'onenote', 'local')
        """
        self.asr_url = asr_url
        self.note_storage = note_storage
        self.onenote_config = {
            'client_id': onenote_client_id,
            'tenant_id': onenote_tenant_id,
            'client_secret': onenote_client_secret
        }
        self.summarizer_model = summarizer_model

        # Initialize components
        self.microphone = None
        self.summarizer = None
        self.onenote = None
        self.local_notes = None

        self._check_dependencies()
        self._initialize_components()

    def _check_dependencies(self):
        """Check if all required dependencies are available."""
        missing_deps = []

        if not PYAUDIO_AVAILABLE:
            missing_deps.append("PyAudio (for microphone recording)")

        if not TRANSFORMERS_AVAILABLE:
            missing_deps.append("Transformers (for text summarization)")

        # Check note storage dependencies
        if self.note_storage in ['auto', 'onenote'] and not MSGRAPH_AVAILABLE:
            if self.note_storage == 'onenote':
                missing_deps.append("Microsoft Graph SDK (for OneNote)")
            elif self.note_storage == 'auto':
                print("⚠️  Microsoft Graph SDK not available, will use local notes")

        if missing_deps:
            print("⚠️  Missing optional dependencies:")
            for dep in missing_deps:
                print(f"   - {dep}")
            print("\n📦 Install all dependencies:")
            print("   pip install -r requirements_test.txt")
            print("\n🔧 For PyAudio on Ubuntu:")
            print("   sudo apt-get install portaudio19-dev python3-pyaudio")
            print("   pip install pyaudio")
            print("   pip install pyaudio")

    def _initialize_components(self):
        """Initialize all components."""
        try:
            # Initialize microphone (optional)
            if PYAUDIO_AVAILABLE:
                self.microphone = MicrophoneRecorder(self.asr_url)
                print("🎤 Microphone component initialized")
            else:
                print("⚠️  Microphone component not available")

            # Initialize summarizer (optional)
            if TRANSFORMERS_AVAILABLE:
                from .summarizer import SummarizationConfig
                config = SummarizationConfig.get_model_config(self.summarizer_model)
                self.summarizer = TextSummarizer(**config)
                print("🤖 Summarizer component initialized")
            else:
                print("⚠️  Summarizer component not available")

            # Initialize note storage
            if self.note_storage == 'onenote' and MSGRAPH_AVAILABLE and self.onenote_config['client_id']:
                self.onenote = OneNoteManager(**self.onenote_config)
                print("📓 OneNote component initialized")
            elif self.note_storage == 'local' or (self.note_storage == 'auto' and not (MSGRAPH_AVAILABLE and self.onenote_config['client_id'])):
                self.local_notes = LocalNoteManager()
                print("📁 Local notes component initialized")
                if self.note_storage == 'auto':
                    print("   (Using local notes as fallback)")
            else:
                print("⚠️  No note storage available")
                if self.note_storage == 'onenote':
                    print("   (OneNote requires Azure credentials)")

        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")

    def process_audio_file(self, audio_file: str, title: Optional[str] = None,
                          create_note: bool = True) -> Dict[str, Any]:
        """
        Process an audio file: transcribe, summarize, and create OneNote.

        Args:
            audio_file: Path to audio file
            title: Custom title for the note
            create_note: Whether to create OneNote entry

        Returns:
            Processing results dictionary
        """
        results = {
            'success': False,
            'transcription': None,
            'summary': None,
            'note_created': False,
            'processing_time': 0,
            'error': None
        }

        start_time = time.time()

        try:
            # Step 1: Transcribe audio
            print(f"🎵 Processing audio file: {audio_file}")
            transcription = self._transcribe_audio_file(audio_file)

            if not transcription:
                results['error'] = "Failed to transcribe audio"
                return results

            results['transcription'] = transcription
            print(f"📝 Transcription complete ({len(transcription)} characters)")

            # Step 2: Summarize transcription
            summary = self._summarize_text(transcription)
            results['summary'] = summary

            if summary:
                print(f"📋 Summary generated ({len(summary)} characters)")
            else:
                print("⚠️  Summary generation failed, using truncated transcription")
                results['summary'] = transcription[:500] + "..." if len(transcription) > 500 else transcription

            # Create OneNote (if enabled)
            if create_note and (self.onenote or self.local_notes):
                note_created = self._create_note(title, transcription, summary, audio_file)
                results['note_created'] = note_created

                if note_created:
                    storage_type = "OneNote" if self.onenote else "local file"
                    print(f"✅ Note created successfully in {storage_type}")
                else:
                    print("❌ Failed to create note")
            elif create_note and not (self.onenote or self.local_notes):
                print("⚠️  No note storage configured, skipping note creation")

            results['success'] = True
            results['processing_time'] = time.time() - start_time

            print(f"⏱️  Processing time: {results['processing_time']:.2f} seconds")
        except Exception as e:
            results['error'] = str(e)
            results['processing_time'] = time.time() - start_time
            print(f"❌ Processing failed: {e}")

        return results

    def process_live_recording(self, duration: float = 10.0,
                              title: Optional[str] = None,
                              create_note: bool = True) -> Dict[str, Any]:
        """
        Record live audio and process it.

        Args:
            duration: Recording duration in seconds
            title: Custom title for the note
            create_note: Whether to create OneNote entry

        Returns:
            Processing results dictionary
        """
        if not self.microphone:
            return {
                'success': False,
                'error': 'Microphone component not available'
            }

        results = {
            'success': False,
            'transcription': None,
            'summary': None,
            'note_created': False,
            'processing_time': 0,
            'error': None
        }

        start_time = time.time()

        try:
            # Record and transcribe in one step
            print(f"🎤 Recording for {duration} seconds...")
            transcription = self.microphone.record_and_transcribe(duration=duration)

            if not transcription:
                results['error'] = "Failed to record or transcribe audio"
                return results

            results['transcription'] = transcription
            print(f"📝 Live transcription complete ({len(transcription)} characters)")

            # Summarize
            summary = self._summarize_text(transcription)
            results['summary'] = summary or transcription[:500] + "..."

            # Create note
            if create_note and (self.onenote or self.local_notes):
                # Save temporary audio file for metadata (needed for both storage types)
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_filename = temp_file.name

                try:
                    if self.microphone.save_recording(temp_filename):
                        note_created = self._create_note(title, transcription, summary, temp_filename)
                        results['note_created'] = note_created
                        if note_created:
                            storage_type = "OneNote" if self.onenote else "local file"
                            print(f"✅ Note created successfully in {storage_type}")
                    else:
                        results['note_created'] = False
                        print("❌ Failed to save temporary audio file")
                finally:
                    if os.path.exists(temp_filename):
                        os.unlink(temp_filename)
            elif create_note and not (self.onenote or self.local_notes):
                print("⚠️  No note storage configured, skipping note creation")

            results['success'] = True
            results['processing_time'] = time.time() - start_time

        except Exception as e:
            results['error'] = str(e)
            results['processing_time'] = time.time() - start_time

        return results

    def _transcribe_audio_file(self, audio_file: str) -> Optional[str]:
        """Transcribe audio file using ASR service."""
        if not self.microphone:
            return None

        try:
            return self.microphone.transcribe_recording(audio_file)
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return None

    def _summarize_text(self, text: str) -> Optional[str]:
        """Summarize text using summarizer component."""
        if not self.summarizer:
            return None

        try:
            return self.summarizer.summarize(text)
        except Exception as e:
            print(f"❌ Summarization failed: {e}")
            return None

    def _create_note(self, title: Optional[str], transcription: str,
                    summary: Optional[str], audio_file: str) -> bool:
        """Create a note using the configured storage method."""
        if not self.onenote and not self.local_notes:
            print("❌ No note storage available")
            return False

        try:
            # Generate title if not provided
            if not title:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                title = f"AI Note {timestamp}"

            # Ensure summary is not None
            if not summary:
                summary = transcription[:500] + "..." if len(transcription) > 500 else transcription

            # Get audio file metadata
            metadata = self._get_audio_metadata(audio_file)

            # Create note based on storage method
            if self.onenote:
                # Use OneNote
                return self.onenote.create_transcription_note(
                    transcription=transcription,
                    summary=summary,
                    title=title,
                    metadata=metadata
                )
            elif self.local_notes:
                # Use local notes
                return bool(self.local_notes.create_note(
                    title=title,
                    transcription=transcription,
                    summary=summary,
                    metadata=metadata
                ))
            else:
                return False

        except Exception as e:
            print(f"❌ Failed to create note: {e}")
            return False

    def _get_audio_metadata(self, audio_file: str) -> Dict[str, Any]:
        """Extract metadata from audio file."""
        metadata = {}

        try:
            # Get file size
            file_size = os.path.getsize(audio_file)
            metadata['file_size_bytes'] = file_size
            metadata['file_size_mb'] = round(file_size / (1024 * 1024), 2)

            # Get file modification time
            mod_time = os.path.getmtime(audio_file)
            metadata['created_timestamp'] = datetime.fromtimestamp(mod_time).isoformat()

            # Try to get audio duration (if wave file)
            if audio_file.lower().endswith('.wav'):
                try:
                    import wave
                    with wave.open(audio_file, 'rb') as wf:
                        frames = wf.getnframes()
                        rate = wf.getframerate()
                        duration = frames / float(rate)
                        metadata['duration_seconds'] = round(duration, 2)
                except:
                    pass

        except Exception as e:
            print(f"⚠️  Failed to extract audio metadata: {e}")

        return metadata


def main():
    """Command-line interface for auto-note processing."""
    import argparse

    parser = argparse.ArgumentParser(description="Auto-Note Processor for TTS AI Pipeline")
    parser.add_argument('--audio-file', help='Path to audio file to process')
    parser.add_argument('--record', action='store_true', help='Record live audio')
    parser.add_argument('--duration', type=float, default=10.0, help='Recording duration in seconds')
    parser.add_argument('--title', help='Custom title for the note')
    parser.add_argument('--no-note', action='store_true', help='Skip OneNote creation')
    parser.add_argument('--asr-url', default='http://localhost:8000', help='ASR service URL')
    parser.add_argument('--onenote-client-id', help='Azure app client ID')
    parser.add_argument('--onenote-tenant-id', help='Azure tenant ID')
    parser.add_argument('--onenote-client-secret', help='Azure app client secret')
    parser.add_argument('--summarizer-model', default='medium', choices=['small', 'medium', 'large'],
                       help='Summarization model size')
    parser.add_argument('--note-storage', default='auto', choices=['auto', 'onenote', 'local'],
                       help='Note storage method (auto=prefer OneNote, fallback to local)')
    parser.add_argument('--local-notes-dir', help='Directory for local notes (default: ~/tts_ai_notes)')

    args = parser.parse_args()

    try:
        # Initialize processor
        processor = AutoNoteProcessor(
            asr_url=args.asr_url,
            onenote_client_id=args.onenote_client_id,
            onenote_tenant_id=args.onenote_tenant_id,
            onenote_client_secret=args.onenote_client_secret,
            summarizer_model=args.summarizer_model,
            note_storage=args.note_storage
        )

        # Configure local notes directory if specified
        if args.local_notes_dir and hasattr(processor, 'local_notes') and processor.local_notes:
            # Re-initialize local notes with custom directory
            from .local_notes import LocalNoteManager
            processor.local_notes = LocalNoteManager(base_dir=args.local_notes_dir)

        # Process audio
        if args.audio_file:
            print(f"🎵 Processing audio file: {args.audio_file}")
            results = processor.process_audio_file(
                audio_file=args.audio_file,
                title=args.title,
                create_note=not args.no_note
            )

        elif args.record:
            print(f"🎤 Recording live audio for {args.duration} seconds...")
            results = processor.process_live_recording(
                duration=args.duration,
                title=args.title,
                create_note=not args.no_note
            )

        else:
            print("❌ Please specify --audio-file or --record")
            return 1

        # Display results
        print("\n" + "="*60)
        print("📊 PROCESSING RESULTS")
        print("="*60)

        if results['success']:
            print("✅ Processing completed successfully!")
            print(".2f")

            if results['transcription']:
                print(f"📝 Transcription: {len(results['transcription'])} characters")
                print(f"   Preview: {results['transcription'][:100]}...")

            if results['summary']:
                print(f"📋 Summary: {len(results['summary'])} characters")
                print(f"   Preview: {results['summary'][:100]}...")

            if results['note_created']:
                print("📓 OneNote: Created successfully")
            elif not args.no_note:
                print("📓 OneNote: Skipped or failed")

        else:
            print("❌ Processing failed!")
            if results['error']:
                print(f"   Error: {results['error']}")

        print("="*60)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
