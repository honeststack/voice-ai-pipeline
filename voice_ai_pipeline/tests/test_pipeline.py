#!/usr/bin/env python3
"""
TTS AI Pipeline Testing with pytest

This module tests all components of the TTS AI Pipeline:
- ASR Service (port 8000)
- TTS Service (port 8001)
- Interface Service (port 7860)
- Microphone functionality (if available)
- Full pipeline integration

Usage:
    pytest voice_ai_pipeline/tests/test_pipeline.py -v

Requirements:
    - requests
    - Docker containers running on expected ports
    - pyaudio (for microphone testing)
"""

import pytest
import requests
import json
import time
import tempfile
import os
import subprocess
from typing import Dict, Any, Tuple

# Service URLs
ASR_BASE_URL = "http://localhost:8000"
TTS_BASE_URL = "http://localhost:8001"
INTERFACE_URL = "http://localhost:7860"


@pytest.fixture(scope="session")
def docker_containers():
    """Fixture to manage Docker containers for testing."""
    containers_started = False

    def start_containers():
        """Start all Docker containers for testing."""
        print("🐳 Starting Docker containers for testing...")

        try:
            # First, stop any running service containers to ensure clean start
            expected_containers = ["voice-ai-service"]
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            running_containers = [name for name in result.stdout.strip().split('\n') if name]
            containers_to_stop = [name for name in running_containers if name in expected_containers]
            if containers_to_stop:
                print(f"   🛑 Stopping running containers: {', '.join(containers_to_stop)}")
                subprocess.run(["docker", "stop"] + containers_to_stop, capture_output=True)
                print(f"   ✅ Stopped containers: {', '.join(containers_to_stop)}")

            # Check if containers are already running
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            running_containers = [name for name in result.stdout.strip().split('\n') if name]

            # Check for our specific service containers
            found_containers = [name for name in running_containers if name in expected_containers]

            # Check all containers (running or stopped)
            all_result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            all_containers = [name for name in all_result.stdout.strip().split('\n') if name]
            existing_containers = [name for name in all_containers if name in expected_containers]

            if len(found_containers) == 1:  # All services should be running in one container
                print(f"   📦 Found running container: {', '.join(found_containers)}")
                return True
            elif len(found_containers) >= 1:  # At least 1 service is running, check for existing stopped containers
                print(f"   ⚠️  Found running container: {', '.join(found_containers)}")
                print("   🔍 Checking for existing stopped containers...")

                # Check all containers (running or stopped)
                all_result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "name=-service", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                all_containers = [name for name in all_result.stdout.strip().split('\n') if name and not name.startswith('buildx')]
                existing_containers = [name for name in all_containers if any(expected in name for expected in expected_containers)]

                # Start existing containers that are not running
                containers_to_start = [name for name in expected_containers if name in existing_containers and name not in found_containers]
                if containers_to_start:
                    print(f"   🚀 Starting stopped containers: {', '.join(containers_to_start)}")
                    subprocess.run(["docker", "start"] + containers_to_start, capture_output=True)
                    time.sleep(5)  # Wait for services to start
                    return True
                else:
                    print("   ❌ No containers to start")
                    return False
            else:
                print("   ❌ No service containers found")
                return False

        except subprocess.CalledProcessError as e:
            print(f"   ❌ Docker command failed: {e}")
            return False
        except FileNotFoundError:
            print("   ❌ Docker not found. Please ensure Docker is installed and running.")
            return False

    def stop_containers():
        """Stop test containers."""
        print("🛑 Stopping test containers...")
        try:
            # Check which containers exist
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=-service", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            all_containers = [name for name in result.stdout.strip().split('\n') if name]

            # Only stop containers we created or that match our service names
            containers_to_stop = []
            for container in all_containers:
                if container in ["voice-ai-test"] or \
                   container in ["voice-ai-service"]:
                    containers_to_stop.append(container)

            if containers_to_stop:
                # Stop containers
                subprocess.run(["docker", "stop"] + containers_to_stop, capture_output=True)
                print(f"   ✅ Stopped containers: {', '.join(containers_to_stop)}")
            else:
                print("   ℹ️  No test containers to stop")

        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: Could not stop containers: {e}")

    # Setup
    containers_started = start_containers()
    if not containers_started:
        pytest.skip("Docker containers could not be started")

    yield containers_started

    # Teardown
    stop_containers()


def test_service_health(docker_containers):
    """Test service health endpoints."""
    services = [
        ("ASR", ASR_BASE_URL),
        ("TTS", TTS_BASE_URL),
        ("Interface", INTERFACE_URL)
    ]

    for service_name, url in services:
        response = requests.get(f"{url}/health", timeout=10)
        assert response.status_code == 200, f"{service_name} health check failed with status {response.status_code}"

        data = response.json()
        assert data.get("healthy") == True, f"{service_name} reports unhealthy"


def test_service_info(docker_containers):
    """Test service info endpoints."""
    services = [
        ("ASR", ASR_BASE_URL),
        ("TTS", TTS_BASE_URL),
        ("Interface", INTERFACE_URL)
    ]

    for service_name, url in services:
        response = requests.get(f"{url}/info", timeout=10)
        assert response.status_code == 200, f"{service_name} info check failed with status {response.status_code}"

        data = response.json()
        assert "model_name" in data or "version" in data, f"{service_name} info missing expected fields"


@pytest.mark.integration
def test_asr_transcription(docker_containers):
    """Test ASR transcription with a sample audio file."""
    # Create a simple test audio file (this would be a real WAV in practice)
    test_text = "Hello, this is a test of the ASR system."

    try:
        # First, let's use TTS to create test audio
        tts_response = requests.post(
            f"{TTS_BASE_URL}/synthesize",
            json={"text": test_text},
            timeout=30
        )

        assert tts_response.status_code == 200, f"TTS synthesis failed: HTTP {tts_response.status_code}"

        # Test ASR transcription
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(tts_response.content)
            audio_path = temp_file.name

        try:
            with open(audio_path, "rb") as audio_file:
                files = {"file": audio_file}
                asr_response = requests.post(
                    f"{ASR_BASE_URL}/transcribe",
                    files=files,
                    timeout=30
                )

            assert asr_response.status_code == 200, f"ASR transcription failed: HTTP {asr_response.status_code}"

            data = asr_response.json()
            transcribed_text = data.get("text", "").strip()

            # Basic validation - should contain some text
            assert len(transcribed_text) > 0, "ASR returned empty transcription"

        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    except requests.exceptions.RequestException as e:
        pytest.fail(f"ASR transcription test failed: {e}")


@pytest.mark.integration
def test_tts_synthesis(docker_containers):
    """Test TTS synthesis."""
    test_text = "This is a test of the text to speech system."

    try:
        response = requests.post(
            f"{TTS_BASE_URL}/synthesize",
            json={"text": test_text},
            timeout=30
        )

        assert response.status_code == 200, f"TTS synthesis failed: HTTP {response.status_code}"

        # Check that we got audio data (WAV file)
        assert len(response.content) > 0, "TTS returned empty audio data"
        assert response.headers.get("content-type") in ["audio/wav", "audio/x-wav", "application/octet-stream"], \
               f"Unexpected content type: {response.headers.get('content-type')}"

    except requests.exceptions.RequestException as e:
        pytest.fail(f"TTS synthesis test failed: {e}")


@pytest.mark.integration
def test_full_pipeline(docker_containers):
    """Test full pipeline: Text -> Speech -> Text."""
    original_text = "The quick brown fox jumps over the lazy dog."

    try:
        # Step 1: Text to Speech
        print("   Step 1: Converting text to speech...")
        tts_response = requests.post(
            f"{TTS_BASE_URL}/synthesize",
            json={"text": original_text},
            timeout=30
        )

        assert tts_response.status_code == 200, f"TTS failed: HTTP {tts_response.status_code}"

        # Step 2: Speech to Text
        print("   Step 2: Converting speech to text...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(tts_response.content)
            audio_path = temp_file.name

        try:
            with open(audio_path, "rb") as audio_file:
                files = {"file": audio_file}
                asr_response = requests.post(
                    f"{ASR_BASE_URL}/transcribe",
                    files=files,
                    timeout=30
                )

            assert asr_response.status_code == 200, f"ASR failed: HTTP {asr_response.status_code}"

            # Step 3: Compare results
            data = asr_response.json()
            final_text = data.get("text", "").strip()

            # Simple accuracy check
            original_words = set(original_text.lower().split())
            final_words = set(final_text.lower().split())
            common_words = original_words.intersection(final_words)
            accuracy = len(common_words) / len(original_words) if original_words else 0

            # Assert reasonable accuracy (at least 50%)
            assert accuracy >= 0.5, f"Round-trip accuracy too low: {accuracy:.1%}"

        finally:
            if os.path.exists(audio_path):
                os.unlink(audio_path)

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Full pipeline test failed: {e}")


def test_microphone_setup():
    """Test microphone setup and availability."""
    try:
        # Try to import microphone module
        try:
            from voice_ai_pipeline.microphone import MicrophoneRecorder, PYAUDIO_AVAILABLE
            if not PYAUDIO_AVAILABLE:
                pytest.skip("PyAudio not available - microphone testing skipped")
        except ImportError:
            pytest.skip("Microphone module not available (pyaudio not installed)")

        recorder = MicrophoneRecorder(ASR_BASE_URL)

        try:
            # Test device listing
            devices = recorder.list_devices()
            assert len(devices) > 0, "No audio input devices found"

            # Test default device
            default_device = recorder.get_default_input_device()
            assert default_device is not None, "No default input device available"

        finally:
            recorder.cleanup()

    except Exception as e:
        pytest.fail(f"Microphone setup test failed: {e}")


def test_auto_note_setup():
    """Test auto-note component setup and dependencies."""
    try:
        # Test imports
        from voice_ai_pipeline import auto_note
        from voice_ai_pipeline import onenote_manager
        from voice_ai_pipeline import local_notes

        # Test that key functions exist
        assert hasattr(auto_note, 'main'), "auto_note module missing main function"
        assert hasattr(onenote_manager, 'OneNoteManager'), "onenote_manager module missing OneNoteManager class"
        assert hasattr(local_notes, 'LocalNoteManager'), "local_notes module missing LocalNoteManager class"

    except (ImportError, Exception) as e:
        pytest.fail(f"Auto-note setup test failed: {e}")


@pytest.mark.integration
def test_interface_service(docker_containers):
    """Test interface service functionality."""
    try:
        # Test basic interface access
        response = requests.get(INTERFACE_URL, timeout=10)
        # Interface might redirect or return HTML
        assert response.status_code in [200, 302], f"Interface service returned status {response.status_code}"

    except requests.exceptions.RequestException as e:
        pytest.fail(f"Interface service test failed: {e}")