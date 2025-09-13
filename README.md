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
  - Docker and Docker Compose
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
   git clone https://github.com/thephiltacular/tts-ai-pipeline.git
   cd tts-ai-pipeline
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

4. **Build Docker images**:
   ```bash
   docker build -f docker/asr.Dockerfile -t tts-asr:latest .
   docker build -f docker/tts.Dockerfile -t tts-tts:latest .
   docker build -f docker/interface.Dockerfile -t tts-interface:latest .
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
   - Speak a short phrase
   - Verify transcription appears
   - Listen to the generated audio output

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
python -m tts_ai_pipeline.asr

# TTS Service
python -m tts_ai_pipeline.tts

# Interface
python -m tts_ai_pipeline.interface
```

Adjust environment variables for local URLs.

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
black tts_ai_pipeline/
isort tts_ai_pipeline/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for ASR capabilities
- [Coqui TTS](https://github.com/coqui-ai/TTS) for text-to-speech synthesis
- [Gradio](https://gradio.app/) for the web interface
- [FastAPI](https://fastapi.tiangolo.com/) for API services
- [Kubernetes](https://kubernetes.io/) for container orchestration