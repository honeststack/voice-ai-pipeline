# TTS AI Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A containerized Text-to-Speech (TTS) AI pipeline with Automatic Speech Recognition (ASR) capabilities, orchestrated using Kubernetes. Built with Python, leveraging local AI models for efficient, private processing on GPU hardware.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Testing](#testing)
- [Configuration](#configuration)
- [Optimization](#optimization)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The TTS AI Pipeline enables real-time voice-to-speech conversion through a web interface. Users can speak into their microphone, have their speech transcribed via ASR, and receive synthesized speech output. The system uses local AI models (Whisper for ASR, Coqui TTS for synthesis) running in containers, ensuring data privacy and leveraging GPU acceleration for performance.

Ideal for applications requiring offline speech processing, such as voice assistants, accessibility tools, or content creation workflows.

## Features

- **ASR Integration**: Automatic speech recognition using OpenAI's Whisper models
- **TTS Synthesis**: High-quality text-to-speech using Coqui TTS models
- **Web Interface**: Gradio-based UI with microphone input support
- **Auto-Note Creation**: Automatically transcribe, summarize, and create notes in Microsoft OneNote
- **Containerized**: Docker containers for easy deployment and scaling
- **Kubernetes Orchestration**: Managed deployment with GPU resource allocation
- **Configurable Models**: Top-level configuration for selecting AI models
- **GPU Acceleration**: Optimized for NVIDIA GPUs with CUDA support
- **Local Processing**: No external API calls; all processing happens locally
- **Optimization Tools**: Scripts to benchmark and select optimal models

## Architecture

The pipeline consists of three main components:

1. **ASR Service**: FastAPI application running Whisper for speech-to-text transcription
2. **TTS Service**: FastAPI application running Coqui TTS for text-to-speech synthesis
3. **Interface Service**: Gradio web application coordinating ASR and TTS services with microphone access

Components communicate via Kubernetes services, with GPU resources allocated as needed.

```
[User Microphone] -> [Gradio Interface] -> [ASR Service] -> [TTS Service] -> [Audio Output]
```

## Prerequisites

- **Hardware**:
  - NVIDIA GPU with at least 8GB VRAM (24GB recommended for larger models)
  - 16GB+ RAM
  - Linux/Windows/macOS with Docker support

- **Software**:
  - Docker and Docker Compose (with Buildx support)
  - Kubernetes cluster (local: minikube/kind, or cloud: GKE/EKS)
  - kubectl configured for your cluster
  - NVIDIA Container Toolkit (for GPU support)
  - Python 3.10+ (for local development)

- **Knowledge**:
  - Basic understanding of Docker and Kubernetes
  - Familiarity with terminal commands

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/thephiltacular/voice-ai-pipeline.git
   cd voice-ai-pipeline
   ```

2. **Set up Python environment** (optional, for development):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```

3. **Configure Kubernetes cluster**:
   - For local development with GPU:
     ```bash
     # Using minikube
     minikube start --driver=docker --gpus=all
     ```
   - Ensure NVIDIA device plugin is installed in your cluster

4. **Build Docker images** (optional - test script handles this automatically):
   ```bash
   # Using Docker Buildx (recommended)
   docker buildx build -f docker/asr.Dockerfile -t asr:latest --load .
   docker buildx build -f docker/tts.Dockerfile -t tts:latest --load .
   docker buildx build -f docker/interface.Dockerfile -t interface:latest --load .

   # Or using legacy Docker build
   docker build -f docker/asr.Dockerfile -t asr:latest .
   docker build -f docker/tts.Dockerfile -t tts:latest .
   docker build -f docker/interface.Dockerfile -t interface:latest .
   ```

## Quickstart

1. **Deploy to Kubernetes**:
   ```bash
   kubectl apply -f k8s/
   ```

2. **Check deployment status**:
   ```bash
   kubectl get pods
   kubectl get services
   ```

3. **Access the web interface**:
   - Get the service IP: `kubectl get svc interface-service`
   - Open `http://<SERVICE_IP>:7860` in your browser
   - Click the microphone button, speak, and receive transcribed text and synthesized speech

4. **Test the pipeline**:
   - Use the comprehensive testing script: `make test`
   - Or run manually: `python -m voice_ai_pipeline.test_pipeline`
   - The script tests all services and full pipeline integration

## Usage

### Web Interface

1. Open the Gradio interface in your browser
2. Click the microphone icon to start recording
3. Speak clearly into your microphone
4. Wait for processing (ASR transcription + TTS synthesis)
5. Review the transcribed text and play the synthesized audio

### API Usage

The ASR and TTS services expose REST APIs:

**ASR Service** (Port 8000):
```bash
curl -X POST -F "file=@audio.wav" http://asr-service:8000/transcribe
```

**TTS Service** (Port 8001):
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!"}' \
  http://tts-service:8001/synthesize \
  --output output.wav
```

### Local Development

Run components individually for testing:

```bash
# ASR Service
python -m voice_ai_pipeline.asr

# TTS Service
python -m voice_ai_pipeline.tts

# Interface
python -m voice_ai_pipeline.interface
```

Adjust environment variables for local URLs.

## Testing

### Automated Testing

Run the full test suite using Make:
```bash
make test
```

Or run the script as a module:
```bash
python -m voice_ai_pipeline.tests.test_pipeline
```

Or use the installed console script:
```bash
test-pipeline
```

The test script will automatically:
- Start all required Docker containers
- Run comprehensive tests on all services
- Test microphone functionality (if available)
- Stop and clean up containers when done

### Microphone Testing

Test microphone recording and ASR transcription:
```bash
make test-microphone
```

List available audio devices:
```bash
make list-devices
```

Or use the microphone component directly:
```bash
# List devices
python -m voice_ai_pipeline.microphone --list-devices

# Test recording and transcription
python -m voice_ai_pipeline.microphone --test

# Record to file
python -m voice_ai_pipeline.microphone --output recording.wav --duration 10

# Interactive recording
python -m voice_ai_pipeline.microphone
```

#### Microphone Setup

The microphone component requires PyAudio, which needs system audio libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
```bash
pip install pyaudio
```

If PyAudio is not available, microphone testing will be skipped gracefully.

### What the Test Script Validates

The testing script (`voice_ai_pipeline/tests/test_pipeline.py`) performs the following tests:

1. **Service Health Checks**:
   - ASR service health endpoint (`/health`)
   - TTS service health endpoint (`/health`)
   - Interface service accessibility

2. **Service Information**:
   - ASR model and device information (`/info`)
   - TTS model and device information (`/info`)

3. **Individual Functionality**:
   - TTS synthesis (text-to-speech conversion)
   - ASR transcription (speech-to-text conversion)

4. **Full Pipeline Integration**:
   - End-to-end test: Text → TTS → Audio → ASR → Text
   - Round-trip accuracy measurement

### Test Requirements

- Docker containers must be running on expected ports
- Python requests library (`pip install -r requirements_test.txt`)
- Network connectivity to service endpoints

### Test Output

The script provides detailed output including:
- ✅/❌ Pass/fail status for each test
- Performance metrics (file sizes, accuracy percentages)
- Error messages for failed tests
- Final summary with pass/fail counts

### Kubernetes Testing

The project includes comprehensive Kubernetes testing capabilities to validate deployments, services, and end-to-end functionality in containerized environments.

#### Quick Kubernetes Test

Run tests against an existing Kubernetes deployment:
```bash
make test-k8s-quick
```

#### Full Kubernetes Test Suite

Run complete test suite including setup, deployment, and testing:
```bash
make test-k8s-full
```

#### Individual Kubernetes Test Commands

```bash
# Setup and deploy to Kubernetes
make test-k8s-setup

# Run tests only (deployment must exist)
make test-k8s-test

# Setup port forwarding for local testing
make test-k8s-port-forward

# Show service URLs
make test-k8s-urls

# Clean up Kubernetes resources
make test-k8s-cleanup

# Test with Minikube
make test-k8s-minikube

# Check deployment health
make test-k8s-health
```

#### Using the Test Script Directly

The Kubernetes test script provides more granular control:

```bash
# Show help
./scripts/test-k8s.sh help

# Full test suite
./scripts/test-k8s.sh full

# Quick test (deployment must exist)
./scripts/test-k8s.sh quick

# Setup and deploy only
./scripts/test-k8s.sh setup

# Run tests only
./scripts/test-k8s.sh test

# Setup port forwarding
./scripts/test-k8s.sh port-forward

# Show service URLs
./scripts/test-k8s.sh urls

# Clean up resources
./scripts/test-k8s.sh cleanup
```

#### Kubernetes Test Features

The Kubernetes test suite validates:

1. **Cluster Connectivity**:
   - kubectl configuration and cluster access
   - Kubernetes API server connectivity

2. **Deployment Status**:
   - Pod creation and scheduling
   - Container startup and health checks
   - Resource allocation (CPU, memory, GPU)

3. **Service Configuration**:
   - Service discovery and DNS resolution
   - Load balancer configuration
   - Network policies and security

4. **Pod Health**:
   - Container health probes
   - Resource utilization monitoring
   - Log aggregation and error detection

5. **Load Balancing**:
   - Service endpoint distribution
   - Traffic routing and failover
   - Session persistence (if configured)

6. **End-to-End Functionality**:
   - API endpoint accessibility
   - Service-to-service communication
   - Data flow through the pipeline

#### Environment Variables for Kubernetes Testing

| Variable | Default | Description |
|----------|---------|-------------|
| `K8S_NAMESPACE` | "default" | Kubernetes namespace for testing |
| `K8S_TIMEOUT` | "300" | Timeout for operations (seconds) |
| `K8S_RETRY_COUNT` | "3" | Number of retry attempts |
| `K8S_PROVIDER` | "" | Kubernetes provider (minikube, etc.) |

Example with custom settings:
```bash
K8S_NAMESPACE=voice-ai K8S_TIMEOUT=600 ./scripts/test-k8s.sh full
```

#### Kubernetes Test Requirements

- kubectl configured and connected to cluster
- Docker for building images (if using local builds)
- Minikube (optional, for local testing)
- Python requests library for API testing

#### Kubernetes Test Output

The test script provides colored output with:
- 🚀 Test suite progress and status
- ✅ Success indicators for passed tests
- ❌ Error details for failed tests
- ⚠️ Warnings for non-critical issues
- ℹ️ Informational messages and URLs

Example output:
```
🚀 Starting Full Kubernetes Test Suite
========================================
✅ kubectl is configured and connected to cluster
✅ All dependencies are available
✅ Minikube is ready
✅ All Docker images built successfully
✅ Images loaded into Minikube
✅ Deployment completed successfully
✅ ASR Service: http://localhost:8000
✅ TTS Service: http://localhost:8001
✅ Interface Service: http://localhost:7860
✅ Test suite completed
🎉 Full test suite completed successfully!
```

## Configuration

### Model Selection

Configure AI models via environment variables in Kubernetes deployments:

- **ASR Model**: Set `ASR_MODEL` (e.g., "small", "medium", "large")
- **TTS Model**: Set `TTS_MODEL` (e.g., "tts_models/en/ljspeech/tacotron2-DDC_ph")

Update `k8s/asr-deployment.yaml` and `k8s/tts-deployment.yaml`, then redeploy:

```bash
kubectl apply -f k8s/asr-deployment.yaml
kubectl apply -f k8s/tts-deployment.yaml
```

### GPU Configuration

GPU resources are automatically allocated. Adjust limits in deployment YAMLs if needed:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ASR_MODEL` | "small" | Whisper model size |
| `TTS_MODEL` | "tts_models/en/ljspeech/tacotron2-DDC_ph" | Coqui TTS model |
| `USE_GPU` | "true" | Enable GPU acceleration |
| `ASR_URL` | "http://asr-service:8000/transcribe" | ASR service endpoint |
| `TTS_URL` | "http://tts-service:8001/synthesize" | TTS service endpoint |

## Optimization

Use included optimization scripts to benchmark and select optimal models:

1. **Prepare sample data**:
   - Place a `sample.wav` file in the project root for ASR benchmarking

2. **Run benchmarks**:
   ```bash
   # After installing the package
   optimize-asr
   optimize-tts
   ```

3. **Interpret results**:
   - Scripts provide load times, processing times, and recommendations
   - Choose models that fit your VRAM while maximizing quality/speed

4. **Update configuration** based on recommendations

## Troubleshooting

### Common Issues

**Pods not starting**:
- Check GPU availability: `nvidia-smi`
- Verify NVIDIA device plugin: `kubectl get pods -n kube-system | grep nvidia`
- Check pod logs: `kubectl logs <pod-name>`

**Out of memory errors**:
- Reduce model size in configuration
- Increase GPU memory limits if available

**Microphone not working**:
- Ensure browser permissions for microphone access
- Test with different browsers
- Check system audio settings

**Slow performance**:
- Use smaller models
- Ensure GPU is being utilized
- Check network latency between services

**Container build failures**:
- Verify Docker has access to GPU
- Check CUDA compatibility
- Update base images if needed

### Logs and Debugging

```bash
# View pod logs
kubectl logs -f <pod-name>

# Check service endpoints
kubectl get endpoints

# Debug network issues
kubectl exec -it <pod-name> -- /bin/bash
```

### Getting Help

- Check GitHub Issues for similar problems
- Ensure all prerequisites are met
- Provide detailed error logs when reporting issues

## Auto-Note Feature

The Auto-Note feature automatically transcribes audio, summarizes the content, and creates structured notes in Microsoft OneNote.

### Features

- **Automatic Transcription**: Uses the ASR service to transcribe audio files or live recordings
- **Intelligent Summarization**: Generates concise summaries using transformer-based models
- **OneNote Integration**: Creates beautifully formatted notes with transcription and summary
- **Flexible Input**: Process existing audio files or record live audio
- **Metadata Tracking**: Includes audio file metadata (duration, size, timestamp)

### Setup

#### Option 1: Local Notes (No Azure Required)

For WSL2 or local development without Azure:

```bash
# Install basic dependencies
pip install -r requirements_test.txt

# Use local note storage (no Azure setup needed)
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --note-storage local
```

#### Option 2: Microsoft OneNote (Requires Azure)

1. **Register an app in Azure AD**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to "Azure Active Directory" > "App registrations"
   - Click "New registration"
   - Name your app (e.g., "TTS AI Pipeline")
   - Set redirect URI type to "Web" with value `http://localhost`

2. **Add OneNote permissions**:
   - In your app registration, go to "API permissions"
   - Click "Add a permission" > "Microsoft Graph"
   - Add these delegated permissions:
     - `Notes.ReadWrite` - Read and write OneNote notebooks
     - `Notes.ReadWrite.All` - Read and write all OneNote notebooks

3. **Get credentials**:
   - Note your "Application (client) ID"
   - Note your "Directory (tenant) ID"
   - Create a client secret in "Certificates & secrets"

4. **Set environment variables**:

```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_SECRET="your-client-secret"
```

### Usage

#### Process Audio File

```bash
# Local notes (no Azure setup required)
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --note-storage local

# OneNote (requires Azure setup)
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --note-storage onenote

# Auto mode (prefers OneNote, falls back to local)
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --note-storage auto

# With custom title
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --title "Meeting Notes"

# Skip note creation (just transcribe and summarize)
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --no-note
```

#### Live Recording

```bash
# Record live audio with local storage
python -m voice_ai_pipeline.auto_note --record --duration 30 --note-storage local

# Record with OneNote
python -m voice_ai_pipeline.auto_note --record --duration 60 --note-storage onenote

# Record with custom settings
python -m voice_ai_pipeline.auto_note --record --duration 60 --title "Interview Notes"
```

#### Advanced Configuration

```bash
# Use different summarization model
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --summarizer-model large

# Specify ASR service URL
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --asr-url http://localhost:8000

# Custom local notes directory
python -m voice_ai_pipeline.auto_note --audio-file recording.wav --note-storage local --local-notes-dir ~/my_notes

# Pass Azure credentials directly
python -m voice_ai_pipeline.auto_note \
  --audio-file recording.wav \
  --note-storage onenote \
  --onenote-client-id "your-client-id" \
  --onenote-tenant-id "your-tenant-id" \
  --onenote-client-secret "your-client-secret"
```

### OneNote Structure

The feature creates a structured notebook hierarchy:

```
📓 AI Transcriptions (Notebook)
└── 📑 Transcriptions (Section)
    ├── 📝 AI Note 20241201_143022
    ├── 📝 Meeting Notes 20241201_150000
    └── 📝 Interview Notes 20241201_160000
```

Each note includes:
- **Title**: Custom or auto-generated timestamp
- **Summary**: AI-generated summary of the transcription
- **Full Transcription**: Complete transcribed text
- **Metadata**: Audio file details (duration, size, creation time)

### Dependencies

- **Microsoft Graph SDK**: For OneNote API integration (optional)
- **Transformers**: For text summarization (BART/T5 models)
- **Azure Identity**: For Microsoft authentication (optional)
- **PyAudio**: For microphone recording (optional)

**Note**: Only transformers is required for basic functionality. Microsoft Graph SDK and Azure Identity are only needed for OneNote integration.

### Troubleshooting

**Authentication Issues**:
- Verify Azure app registration and permissions
- Check client ID, tenant ID, and client secret
- Ensure user has consented to permissions

**Summarization Errors**:
- Install transformers: `pip install transformers sentencepiece`
- Check available GPU memory for larger models
- Use smaller model size if encountering memory issues

**OneNote API Errors**:
- Verify internet connectivity
- Check OneNote service status
- Ensure user has active Microsoft account

**Audio Processing Issues**:
- Test ASR service: `curl http://localhost:8000/health`
- Verify audio file format (WAV recommended)
- Check microphone permissions for live recording

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests
4. Run optimization scripts to ensure performance
5. Commit your changes: `git commit -am 'Add some feature'`
6. Push to the branch: `git push origin feature/your-feature`
7. Submit a pull request

### Development Setup

```bash
# Install in development mode
pip install -e .

# Run tests (if added)
pytest

# Format code
black voice_ai_pipeline/
isort voice_ai_pipeline/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for ASR capabilities
- [Coqui TTS](https://github.com/coqui-ai/TTS) for text-to-speech synthesis
- [Gradio](https://gradio.app/) for the web interface
- [FastAPI](https://fastapi.tiangolo.com/) for API services
- [Kubernetes](https://kubernetes.io/) for container orchestration