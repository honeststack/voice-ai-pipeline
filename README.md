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
- [Copilot MCP Integration](#copilot-mcp-integration)
- [Auto-Note Feature](#auto-note-feature)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The TTS AI Pipeline enables real-time voice-to-speech conversion through a web interface. Users can speak into their microphone, have their speech transcribed via ASR, and receive synthesized speech output. The system uses local AI models (Whisper for ASR, Coqui TTS for synthesis) running in a single optimized container, ensuring data privacy and leveraging GPU acceleration for performance.

**Key Optimization**: All services (ASR, TTS, Interface) run in parallel within a single container, dramatically simplifying deployment while maintaining full functionality and optimal resource utilization.

Ideal for applications requiring offline speech processing, such as voice assistants, accessibility tools, or content creation workflows.

## Features

- **ASR Integration**: Automatic speech recognition using OpenAI's Whisper models
- **TTS Synthesis**: High-quality text-to-speech using Coqui TTS models
- **Web Interface**: Gradio-based UI with microphone input support
- **Auto-Note Creation**: Automatically transcribe, summarize, and create notes in Microsoft OneNote
- **Single-Container Deployment**: All services consolidated into one optimized container with parallel execution
- **Copilot MCP Integration**: Send voice transcriptions to Copilot for AI-powered responses
- **Kubernetes Orchestration**: Managed deployment with GPU resource allocation
- **Configurable Models**: Top-level configuration for selecting AI models
- **GPU Acceleration**: Optimized for NVIDIA GPUs with CUDA support
- **Local Processing**: No external API calls; all processing happens locally
- **Optimization Tools**: Scripts to benchmark and select optimal models

## Architecture

The pipeline runs as a single optimized container with all services operating in parallel:

1. **Unified AI Service**: Single container running ASR, TTS, and Interface services simultaneously
2. **Parallel Processing**: All services start concurrently for optimal resource utilization
3. **Service Selection**: Environment-based configuration determines which services are active

Components communicate internally within the container, with GPU resources allocated efficiently.

```
[User Microphone] -> [Gradio Interface] -> [ASR Service] -> [TTS Service] -> [Audio Output]
                    (All in single container with parallel execution)
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

4. **Build Docker image** (optional - deployment script handles this automatically):
   ```bash
   # Using Docker Buildx (recommended)
   docker buildx build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest --load .

   # Or using legacy Docker build
   docker build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest .
   ```

## Quickstart

1. **Deploy to Kubernetes**:
   ```bash
   make k8s-setup
   ```

2. **Check deployment status**:
   ```bash
   make k8s-status
   ```

3. **Access the web interface**:
   ```bash
   make k8s-urls
   ```
   - Open the provided URL in your browser
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

The unified service exposes REST APIs for all components:

**ASR Service** (Port 8000):
```bash
curl -X POST -F "file=@audio.wav" http://voice-ai-service:8000/transcribe
```

**TTS Service** (Port 8001):
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!"}' \
  http://voice-ai-service:8001/synthesize \
  --output output.wav
```

**Interface Service** (Port 7860):
```bash
curl http://voice-ai-service:7860/health
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


#### Pytest Usage (Recommended)

You can run **all tests** using [pytest](https://docs.pytest.org/):

```bash
pytest voice_ai_pipeline/tests/ -v
```

This will automatically discover and run:
- Pipeline tests (`test_pipeline.py`)
- Kubernetes tests (`test_k8s.py`)
- MCP integration tests (`test_mcp.py`)

**Requirements:**
- Install test dependencies: `pip install -r requirements_test.txt`
- For Kubernetes and MCP tests, ensure services are running or endpoints are available (see below)

#### Makefile and Script-based Testing

You can still use the Makefile or run scripts directly:

```bash
make test
```

Or run the pipeline test as a module:

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

Configure AI models via environment variables in the Kubernetes deployment:

- **ASR Model**: Set `ASR_MODEL` (e.g., "small", "medium", "large")
- **TTS Model**: Set `TTS_MODEL` (e.g., "tts_models/en/ljspeech/tacotron2-DDC_ph")
- **Service Type**: Set `SERVICE_TYPE` to control which services run ("asr", "tts", "interface", or "all")

Update `k8s/voice-ai-deployment.yaml`, then redeploy:

```bash
kubectl apply -f k8s/voice-ai-deployment.yaml
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
| `SERVICE_TYPE` | "all" | Services to run ("asr", "tts", "interface", or "all") |
| `ASR_MODEL` | "small" | Whisper model size |
| `TTS_MODEL` | "tts_models/en/ljspeech/tacotron2-DDC_ph" | Coqui TTS model |
| `USE_GPU` | "true" | Enable GPU acceleration |
| `ASR_URL` | "http://localhost:8000/transcribe" | ASR service endpoint |
| `TTS_URL` | "http://localhost:8001/synthesize" | TTS service endpoint |
| `MCP_ENABLED` | "false" | Enable MCP integration with Copilot |
| `COPILOT_MCP_URL` | "http://localhost:3000/mcp" | MCP server endpoint for Copilot |

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
- Check pod logs: `kubectl logs -f voice-ai-pod`
- Verify single container has all required dependencies

**Service not accessible**:
- Check if all services started in parallel: `kubectl logs voice-ai-pod | grep "Starting"`
- Verify SERVICE_TYPE environment variable is set correctly
- Check internal port mappings within the container

**Out of memory errors**:
- Reduce model size in configuration
- Increase GPU memory limits if available
- Monitor resource usage: `kubectl top pods`

**Microphone not working**:
- Ensure browser permissions for microphone access
- Test with different browsers
- Check system audio settings
- Verify interface service is running: `curl http://voice-ai-service:7860/health`

**Slow performance**:
- Use smaller models
- Ensure GPU is being utilized: `nvidia-smi`
- Check if all services are competing for resources

**Container build failures**:
- Verify Docker has access to GPU
- Check CUDA compatibility
- Update base images if needed
- Ensure all dependencies are included in single container

### Logs and Debugging

```bash
# View pod logs (all services in one container)
kubectl logs -f voice-ai-pod

# Check service endpoints
kubectl get endpoints voice-ai-service

# Debug container issues
kubectl exec -it voice-ai-pod -- /bin/bash

# Monitor resource usage
kubectl top pods

# Check service health
curl http://voice-ai-service:8000/health  # ASR
curl http://voice-ai-service:8001/health  # TTS
curl http://voice-ai-service:7860/health  # Interface
```

### Getting Help

- Check GitHub Issues for similar problems
- Ensure all prerequisites are met
- Provide detailed error logs when reporting issues

## Copilot MCP Integration

The pipeline includes Model Context Protocol (MCP) integration that allows voice transcriptions to be sent directly to Copilot for AI-powered responses. This enables voice-driven AI interactions where you can speak naturally and receive intelligent responses.

### Features

- **Voice-to-Copilot**: Convert speech transcriptions into structured prompts for Copilot
- **Smart Prompt Formatting**: Automatically detect question types and format prompts appropriately
- **Session Management**: Maintain conversation context across interactions
- **Error Handling**: Graceful fallback when MCP services are unavailable
- **Configurable Endpoints**: Flexible MCP server configuration

### Setup

#### Environment Variables

Set the following environment variables to enable MCP integration:

```bash
export MCP_ENABLED="true"
export COPILOT_MCP_URL="http://localhost:3000/mcp"
```

#### MCP Server Requirements

The MCP integration requires a running MCP server that can communicate with Copilot. The server should:

- Accept JSON-RPC 2.0 requests
- Support the `copilot/chat` method
- Handle conversation context
- Return structured responses

### Usage

#### Web Interface

1. Open the Gradio interface
2. Check the "Send to Copilot (MCP)" checkbox
3. Speak into the microphone
4. The transcription will be sent to Copilot and the response will be displayed alongside the transcribed text

#### Programmatic Usage

```python
from voice_ai_pipeline.mcp_client import MCPClient, create_copilot_prompt

# Create MCP client
client = MCPClient()

# Convert transcription to Copilot prompt
transcription = "Can you help me write a Python function?"
prompt = client.create_prompt_from_transcription(transcription)

# Send to Copilot
response = client.send_to_copilot(prompt)
print(response['result'])

# Or use convenience function
response = create_copilot_prompt(transcription)
```

### Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_ENABLED` | "false" | Enable MCP integration |
| `COPILOT_MCP_URL` | "http://localhost:3000/mcp" | MCP server endpoint |
| `MCP_TIMEOUT` | "30" | Request timeout in seconds |
| `MCP_MAX_RETRIES` | "3" | Maximum retry attempts |

### Prompt Types

The MCP client automatically detects and formats different types of prompts:

- **Questions**: "What is Python?", "How do I..."
- **Commands**: "Please create a function for..."
- **Code Requests**: "Write a script that..."
- **General**: All other types of input

### Session Management

The MCP client maintains conversation context:

```python
# Get current session info
session = client.get_session_info()

# Clear session context
client.clear_session()
```

### Error Handling

The integration includes comprehensive error handling:

- Network connectivity issues
- MCP server unavailability
- Invalid responses
- Timeout handling with retry logic

If MCP fails, the pipeline continues to function normally with ASR and TTS only.

### Dependencies

MCP integration requires:
- `requests` (already included)
- Python 3.8+ for type hints

No additional packages are required as the MCP client uses standard library features.

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