# Makefile for TTS AI Pipeline

.PHONY: help install-k8s setup build build-cache build-multi deploy clean dev test lint format

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Install Kubernetes tools (minikube and kubectl)
install-k8s: ## Install minikube and kubectl for local Kubernetes
	@echo "Installing kubectl..."
	curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
	sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
	rm kubectl
	@echo "Installing minikube..."
	curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
	sudo install minikube-linux-amd64 /usr/local/bin/minikube
	rm minikube-linux-amd64
	@echo "Kubernetes tools installed. Run 'minikube start --driver=docker --gpus=all' to start cluster."

# Set up the project (install dependencies)
setup: ## Set up the project by installing Python dependencies
	@echo "Setting up Python virtual environment..."
	python3 -m venv .venv
	@echo "Installing dependencies..."
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -e .
	@echo "Setup complete. Activate venv with: source .venv/bin/activate"

# Build Docker images
build: ## Build all Docker images using Buildx
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name tts-builder 2>/dev/null || docker buildx use tts-builder || true
	@echo "Building ASR Docker image..."
	docker buildx build -f docker/asr.Dockerfile -t tts-asr:latest --load --progress=plain .
	@echo "Building TTS Docker image..."
	docker buildx build -f docker/tts.Dockerfile -t tts-tts:latest --load --progress=plain .
	@echo "Building Interface Docker image..."
	docker buildx build -f docker/interface.Dockerfile -t tts-interface:latest --load --progress=plain .
	@echo "Docker images built successfully."

# Build with cache
build-cache: ## Build Docker images with BuildKit cache
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name tts-builder 2>/dev/null || docker buildx use tts-builder || true
	@echo "Building ASR Docker image with cache..."
	docker buildx build -f docker/asr.Dockerfile -t tts-asr:latest --load --progress=plain --cache-from type=local,src=/tmp/.buildx-cache-asr --cache-to type=local,dest=/tmp/.buildx-cache-asr-new,mode=max .
	@echo "Building TTS Docker image with cache..."
	docker buildx build -f docker/tts.Dockerfile -t tts-tts:latest --load --progress=plain --cache-from type=local,src=/tmp/.buildx-cache-tts --cache-to type=local,dest=/tmp/.buildx-cache-tts-new,mode=max .
	@echo "Building Interface Docker image with cache..."
	docker buildx build -f docker/interface.Dockerfile -t tts-interface:latest --load --progress=plain --cache-from type=local,src=/tmp/.buildx-cache-interface --cache-to type=local,dest=/tmp/.buildx-cache-interface-new,mode=max .
	@echo "Moving cache directories..."
	@mv /tmp/.buildx-cache-asr-new /tmp/.buildx-cache-asr 2>/dev/null || true
	@mv /tmp/.buildx-cache-tts-new /tmp/.buildx-cache-tts 2>/dev/null || true
	@mv /tmp/.buildx-cache-interface-new /tmp/.buildx-cache-interface 2>/dev/null || true
	@echo "Docker images built with cache successfully."

# Build for multiple platforms
build-multi: ## Build Docker images for multiple platforms
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name tts-builder-multi 2>/dev/null || docker buildx use tts-builder-multi || true
	@echo "Building multi-platform ASR Docker image..."
	docker buildx build -f docker/asr.Dockerfile -t tts-asr:latest --platform linux/amd64,linux/arm64 --push .
	@echo "Building multi-platform TTS Docker image..."
	docker buildx build -f docker/tts.Dockerfile -t tts-tts:latest --platform linux/amd64,linux/arm64 --push .
	@echo "Building multi-platform Interface Docker image..."
	docker buildx build -f docker/interface.Dockerfile -t tts-interface:latest --platform linux/amd64,linux/arm64 --push .
	@echo "Multi-platform Docker images built successfully."

# Deploy to Kubernetes
deploy: ## Deploy the application to Kubernetes
	@echo "Applying Kubernetes manifests..."
	kubectl apply -f k8s/
	@echo "Waiting for deployments to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/asr-deployment
	kubectl wait --for=condition=available --timeout=300s deployment/tts-deployment
	kubectl wait --for=condition=available --timeout=300s deployment/interface-deployment
	@echo "Deployment complete. Get service IP with: kubectl get svc interface-service"

# Clean up resources
clean: ## Clean up Docker images and Kubernetes resources
	@echo "Deleting Kubernetes resources..."
	kubectl delete -f k8s/ --ignore-not-found=true
	@echo "Removing Docker images..."
	docker rmi tts-asr:latest tts-tts:latest tts-interface:latest --force 2>/dev/null || true
	@echo "Cleaning up Docker Buildx builder..."
	docker buildx rm tts-builder 2>/dev/null || true
	@echo "Cleaning up temporary files..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete."

# Run in development mode (local services)
dev: ## Run services locally for development
	@echo "Starting ASR service..."
	./.venv/bin/python -m tts_ai_pipeline.asr &
	@echo "Starting TTS service..."
	./.venv/bin/python -m tts_ai_pipeline.tts &
	@echo "Starting Interface..."
	./.venv/bin/python -m tts_ai_pipeline.interface &
	@echo "Services started. Access interface at http://localhost:7860"
	@echo "Stop with: pkill -f 'python -m tts_ai_pipeline'"

# Run optimization scripts
optimize: ## Run model optimization scripts
	@echo "Running ASR optimization..."
	./.venv/bin/python -m tts_ai_pipeline.optimize_asr
	@echo "Running TTS optimization..."
	./.venv/bin/python -m tts_ai_pipeline.optimize_tts

# Lint code
lint: ## Run linting on Python code
	@echo "Running flake8..."
	./.venv/bin/pip install flake8
	./.venv/bin/flake8 tts_ai_pipeline/ --max-line-length=100
	@echo "Linting complete."

# Format code
format: ## Format Python code with black
	@echo "Running black formatter..."
	./.venv/bin/pip install black
	./.venv/bin/black tts_ai_pipeline/
	@echo "Code formatted."

# Check GPU availability
check-gpu: ## Check GPU and CUDA availability
	@echo "Checking GPU..."
	nvidia-smi || echo "NVIDIA GPU not detected"
	@echo "Checking CUDA in PyTorch..."
	./.venv/bin/python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU count:', torch.cuda.device_count())"

# Full setup (setup + build + deploy)
full-setup: setup build deploy ## Complete setup: install deps, build images, deploy to k8s
	@echo "Full setup complete!"

# Stop development services
stop-dev: ## Stop development services
	@echo "Stopping services..."
	pkill -f "python -m tts_ai_pipeline" || true
	@echo "Services stopped."

# Run comprehensive pipeline tests
test: ## Run comprehensive tests on all pipeline components
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Running pipeline tests..."
	./.venv/bin/python -m tts_ai_pipeline.tests.test_pipeline

# Run tests with verbose output
test-verbose: ## Run tests with detailed output
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Running pipeline tests with verbose output..."
	python3 -u -m tts_ai_pipeline.tests.test_pipeline

# Test microphone functionality
test-microphone: ## Test microphone recording and ASR transcription
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Testing microphone functionality..."
	./.venv/bin/python -m tts_ai_pipeline.microphone --test

# List available audio devices
list-devices: ## List available microphone devices
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Listing available audio devices..."
	./.venv/bin/python -m tts_ai_pipeline.microphone --list-devices
