#!/usr/bin/env python3
"""
TTS AI Pipeline Testing Script

This script tests all components of the TTS AI Pipeline:
- ASR Service (port 8000)
- TTS Service (port 8001)
- Interface Service (port 7860)
- Microphone functionality (if available)
- Full pipeline integration

Usage:
    python -m tts_ai_pipeline.tests.test_pipeline

Requirements:
    - requests
    - Docker containers running on expected ports
    - pyaudio (for microphone testing)
"""

import requests
import json
import time
import tempfile
import os
import sys
import subprocess
from typing import Dict, Any, Tuple

# Service URLs
ASR_BASE_URL = "http://localhost:8000"
TTS_BASE_URL = "http://localhost:8001"
INTERFACE_URL = "http://localhost:7860"

class PipelineTester:
    """Test class for TTS AI Pipeline components."""

    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.containers_started = False

    def start_containers(self):
        """Start all Docker containers for testing."""
        print("🐳 Starting Docker containers for testing...")
        
        try:
            # Check if containers are already running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=tts-", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            running_containers = [name for name in result.stdout.strip().split('\n') if name and not name.startswith('buildx')]
            
            # Check for our specific service containers
            expected_containers = ["asr-service", "tts-service", "interface-service"]
            found_containers = [name for name in running_containers if any(expected in name for expected in expected_containers)]
            
            # Check all containers (running or stopped)
            all_result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=tts-", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            all_containers = [name for name in all_result.stdout.strip().split('\n') if name and not name.startswith('buildx')]
            existing_containers = [name for name in all_containers if any(expected in name for expected in expected_containers)]
            
            if len(found_containers) >= 2:  # At least 2 out of 3 services should be running
                print(f"   📦 Found running containers: {', '.join(found_containers)}")
                self.containers_started = True
                return True
            elif len(found_containers) >= 1:  # At least 1 service is running, check for existing stopped containers
                print(f"   ⚠️  Found only {len(found_containers)} running containers: {', '.join(found_containers)}")
                print("   � Checking for existing stopped containers...")
                
                # Check all containers (running or stopped)
                all_result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "name=tts-", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                all_containers = [name for name in all_result.stdout.strip().split('\n') if name and not name.startswith('buildx')]
                existing_containers = [name for name in all_containers if any(expected in name for expected in expected_containers)]
                
                # Start existing containers that are not running
                containers_to_start = [name for name in expected_containers if name in existing_containers and name not in found_containers]
                if containers_to_start:
                    print(f"   � Starting stopped containers: {', '.join(containers_to_start)}")
                    subprocess.run(["docker", "start"] + containers_to_start, check=True)
                    print(f"   ✅ Started containers: {', '.join(containers_to_start)}")
                    # Wait for containers to be ready
                    time.sleep(10)
                    self.containers_started = True
                    return True
                else:
                    print("   🆕 No additional existing containers to start, creating new ones...")
                    # Fall through to create new containers
            else:
                # No containers running, check for existing stopped containers first
                print("   🔍 No running containers found, checking for existing stopped containers...")
                
                # Check all containers (running or stopped)
                all_result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "name=tts-", "--format", "{{.Names}}"],
                    capture_output=True, text=True, check=True
                )
                all_containers = [name for name in all_result.stdout.strip().split('\n') if name and not name.startswith('buildx')]
                existing_containers = [name for name in all_containers if any(expected in name for expected in expected_containers)]
                
                if existing_containers:
                    print(f"   🔄 Found existing containers: {', '.join(existing_containers)}")
                    print("   🚀 Starting existing containers...")
                    # Start existing containers
                    containers_to_start = [name for name in expected_containers if name in existing_containers]
                    if containers_to_start:
                        subprocess.run(["docker", "start"] + containers_to_start, check=True)
                        print(f"   ✅ Started containers: {', '.join(containers_to_start)}")
                        # Wait for containers to be ready
                        time.sleep(10)
                        self.containers_started = True
                        return True
                else:
                    print("   🆕 No existing containers found, creating new ones...")
                    # Fall through to create new containers
            
            # Start containers using docker-compose or docker run
            # First try docker-compose
            compose_file = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")
            if os.path.exists(compose_file):
                print("   📄 Found docker-compose.yml, starting services...")
                subprocess.run(
                    ["docker-compose", "up", "-d"],
                    cwd=os.path.dirname(compose_file),
                    check=True
                )
            else:
                # No containers exist, create new ones
                print("   🆕 No existing containers found, creating new ones...")
                
                # Get the project root directory
                project_root = os.path.join(os.path.dirname(__file__), "..", "..")
                
                # Start ASR container
                try:
                    subprocess.run([
                        "docker", "run", "-d", "--name", "asr-service", 
                        "--gpus", "all", "-p", "8000:8000",
                        "-v", f"{project_root}/models:/app/models",
                        "tts-asr:latest"
                    ], check=True)
                    print("   ✅ Started ASR service")
                except subprocess.CalledProcessError:
                    print("   ❌ Failed to start ASR service")
                
                # Start TTS container
                try:
                    subprocess.run([
                        "docker", "run", "-d", "--name", "tts-service",
                        "--gpus", "all", "-p", "8001:8001", 
                        "-v", f"{project_root}/models:/app/models",
                        "tts-tts:latest"
                    ], check=True)
                    print("   ✅ Started TTS service")
                except subprocess.CalledProcessError:
                    print("   ❌ Failed to start TTS service")
                
                # Start Interface container
                try:
                    subprocess.run([
                        "docker", "run", "-d", "--name", "interface-service",
                        "-p", "7860:7860",
                        "tts-interface:latest"
                    ], check=True)
                    print("   ✅ Started Interface service")
                except subprocess.CalledProcessError:
                    print("   ❌ Failed to start Interface service")
            
            # Wait for containers to be ready
            print("   ⏳ Waiting for containers to start...")
            time.sleep(10)
            
            self.containers_started = True
            print("   ✅ Containers started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to start containers: {e}")
            return False
        except FileNotFoundError:
            print("   ❌ Docker not found. Please ensure Docker is installed and running.")
            return False

    def stop_containers(self):
        """Stop test containers."""
        if not self.containers_started:
            return
            
        print("🛑 Stopping test containers...")
        try:
            # Check which containers exist
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=tts-", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            all_containers = [name for name in result.stdout.strip().split('\n') if name]
            
            # Only stop containers we created or that match our service names
            containers_to_stop = []
            for container in all_containers:
                if container in ["tts-asr-test", "tts-tts-test", "tts-interface-test"] or \
                   container in ["asr-service", "tts-service", "interface-service"]:
                    containers_to_stop.append(container)
            
            if containers_to_stop:
                # Stop containers
                subprocess.run(["docker", "stop"] + containers_to_stop, capture_output=True)
                print(f"   ✅ Stopped containers: {', '.join(containers_to_stop)}")
            else:
                print("   ℹ️  No test containers to stop")
                
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Warning: Could not stop containers: {e}")

    def log_test(self, test_name: str, result: bool, message: str = ""):
        """Log a test result."""
        status = "✅ PASS" if result else "❌ FAIL"
        self.test_results.append(f"{status} {test_name}")
        if message:
            self.test_results.append(f"   {message}")

        if result:
            self.passed += 1
        else:
            self.failed += 1

        print(f"{status} {test_name}")
        if message:
            print(f"   {message}")

    def test_service_health(self, service_name: str, url: str) -> bool:
        """Test service health endpoint."""
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("healthy"):
                    self.log_test(f"{service_name} Health Check", True, f"Service is healthy")
                    return True
                else:
                    self.log_test(f"{service_name} Health Check", False, f"Service reports unhealthy")
                    return False
            else:
                self.log_test(f"{service_name} Health Check", False, f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test(f"{service_name} Health Check", False, f"Connection failed: {e}")
            return False

    def test_service_info(self, service_name: str, url: str) -> bool:
        """Test service info endpoint."""
        try:
            response = requests.get(f"{url}/info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test(f"{service_name} Info Check", True,
                            f"Model: {data.get('model_name', 'N/A')}, Device: {data.get('device', 'N/A')}")
                return True
            else:
                self.log_test(f"{service_name} Info Check", False, f"HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.log_test(f"{service_name} Info Check", False, f"Connection failed: {e}")
            return False

    def test_asr_transcription(self) -> bool:
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

            if tts_response.status_code != 200:
                self.log_test("ASR Transcription Test", False, f"TTS failed to generate test audio: HTTP {tts_response.status_code}")
                return False

            # Save the audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(tts_response.content)
                audio_path = temp_file.name

            try:
                # Now test ASR with the generated audio
                with open(audio_path, "rb") as audio_file:
                    files = {"file": audio_file}
                    asr_response = requests.post(
                        f"{ASR_BASE_URL}/transcribe",
                        files=files,
                        timeout=30
                    )

                if asr_response.status_code == 200:
                    data = asr_response.json()
                    transcribed_text = data.get("text", "").strip()

                    # Calculate simple accuracy (basic word matching)
                    original_words = set(test_text.lower().split())
                    transcribed_words = set(transcribed_text.lower().split())
                    common_words = original_words.intersection(transcribed_words)
                    accuracy = len(common_words) / len(original_words) if original_words else 0

                    self.log_test("ASR Transcription Test", True,
                                f"Original: '{test_text}' | Transcribed: '{transcribed_text}' | Accuracy: {accuracy:.1%}")
                    return True
                else:
                    self.log_test("ASR Transcription Test", False, f"HTTP {asr_response.status_code}")
                    return False

            finally:
                # Clean up temp file
                if os.path.exists(audio_path):
                    os.unlink(audio_path)

        except requests.exceptions.RequestException as e:
            self.log_test("ASR Transcription Test", False, f"Request failed: {e}")
            return False

    def test_tts_synthesis(self) -> bool:
        """Test TTS synthesis."""
        test_text = "This is a test of the text-to-speech synthesis system."

        try:
            response = requests.post(
                f"{TTS_BASE_URL}/synthesize",
                json={"text": test_text},
                timeout=30
            )

            if response.status_code == 200:
                content_length = len(response.content)
                content_type = response.headers.get("content-type", "")

                if content_length > 1000 and "audio" in content_type.lower():
                    self.log_test("TTS Synthesis Test", True,
                                f"Generated {content_length} bytes of audio data")
                    return True
                else:
                    self.log_test("TTS Synthesis Test", False,
                                f"Invalid response: {content_length} bytes, type: {content_type}")
                    return False
            else:
                self.log_test("TTS Synthesis Test", False, f"HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.log_test("TTS Synthesis Test", False, f"Request failed: {e}")
            return False

    def test_interface_accessibility(self) -> bool:
        """Test interface web service accessibility."""
        try:
            response = requests.get(INTERFACE_URL, timeout=10)

            if response.status_code == 200:
                if "html" in response.text.lower() and "gradio" in response.text.lower():
                    self.log_test("Interface Accessibility", True, "Gradio web interface is accessible")
                    return True
                else:
                    self.log_test("Interface Accessibility", False, "Response doesn't contain expected HTML content")
                    return False
            else:
                self.log_test("Interface Accessibility", False, f"HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            self.log_test("Interface Accessibility", False, f"Connection failed: {e}")
            return False

    def test_full_pipeline(self) -> bool:
        """Test the complete pipeline: Text -> TTS -> Audio -> ASR -> Text."""
        original_text = "The quick brown fox jumps over the lazy dog."

        try:
            # Step 1: Text to Speech
            print("   Step 1: Converting text to speech...")
            tts_response = requests.post(
                f"{TTS_BASE_URL}/synthesize",
                json={"text": original_text},
                timeout=30
            )

            if tts_response.status_code != 200:
                self.log_test("Full Pipeline Test", False, f"TTS failed: HTTP {tts_response.status_code}")
                return False

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

                if asr_response.status_code != 200:
                    self.log_test("Full Pipeline Test", False, f"ASR failed: HTTP {asr_response.status_code}")
                    return False

                # Step 3: Compare results
                data = asr_response.json()
                final_text = data.get("text", "").strip()

                # Simple accuracy check
                original_words = set(original_text.lower().split())
                final_words = set(final_text.lower().split())
                common_words = original_words.intersection(final_words)
                accuracy = len(common_words) / len(original_words) if original_words else 0

                self.log_test("Full Pipeline Test", True,
                            f"Original: '{original_text}' | Final: '{final_text}' | Round-trip accuracy: {accuracy:.1%}")
                return True

            finally:
                if os.path.exists(audio_path):
                    os.unlink(audio_path)

        except requests.exceptions.RequestException as e:
            self.log_test("Full Pipeline Test", False, f"Pipeline failed: {e}")
            return False

    def test_microphone_setup(self) -> bool:
        """Test microphone setup and availability."""
        try:
            # Try to import microphone module
            try:
                from ..microphone import MicrophoneRecorder, PYAUDIO_AVAILABLE
                if not PYAUDIO_AVAILABLE:
                    self.log_test("Microphone Setup Test", False, "PyAudio not available - microphone testing skipped")
                    return False
            except ImportError:
                self.log_test("Microphone Setup Test", False, "Microphone module not available (pyaudio not installed)")
                return False

            recorder = MicrophoneRecorder(ASR_BASE_URL)

            try:
                # Test device listing
                devices = recorder.list_devices()
                if not devices:
                    self.log_test("Microphone Setup Test", False, "No audio input devices found")
                    return False

                # Test default device
                default_device = recorder.get_default_input_device()
                if default_device is None:
                    self.log_test("Microphone Setup Test", False, "No default input device available")
                    return False

                device_info = recorder.audio.get_device_info_by_index(default_device)
                device_name = device_info.get('name', f'Device {default_device}')

                self.log_test("Microphone Setup Test", True,
                            f"Found {len(devices)} device(s), using: {device_name}")
                return True

            finally:
                recorder.cleanup()

        except Exception as e:
            self.log_test("Microphone Setup Test", False, f"Microphone setup failed: {e}")
            return False

    def run_all_tests(self):
        """Run all tests."""
        print("🚀 Starting TTS AI Pipeline Testing Suite")
        print("=" * 50)

        # Test individual services
        print("\n🔍 Testing Individual Services:")
        print("-" * 30)

        self.test_service_health("ASR Service", ASR_BASE_URL)
        self.test_service_info("ASR Service", ASR_BASE_URL)

        self.test_service_health("TTS Service", TTS_BASE_URL)
        self.test_service_info("TTS Service", TTS_BASE_URL)

        self.test_interface_accessibility()

        # Test functionality
        print("\n⚙️  Testing Service Functionality:")
        print("-" * 35)

        self.test_tts_synthesis()
        self.test_asr_transcription()

        # Test microphone functionality (optional)
        print("\n🎤 Testing Microphone Functionality:")
        print("-" * 38)

        self.test_microphone_setup()

        # Test full pipeline
        print("\n🔄 Testing Full Pipeline Integration:")
        print("-" * 40)

        self.test_full_pipeline()

        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)

        for result in self.test_results:
            print(result)

        print(f"\n🎯 Results: {self.passed} passed, {self.failed} failed")

        if self.failed == 0:
            print("🎉 ALL TESTS PASSED! Pipeline is fully operational.")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
            return False


def main():
    """Main function."""
    tester = PipelineTester()
    
    # Start containers
    if not tester.start_containers():
        print("❌ Failed to start containers. Aborting tests.")
        sys.exit(1)
    
    try:
        # Run tests
        success = tester.run_all_tests()
    finally:
        # Always stop containers
        tester.stop_containers()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
