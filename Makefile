# Makefile for TTS AI Pipeline

.PHONY: help install-k8s setup build build-cache build-multi build-k8s deploy clean dev test lint format

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

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
	@echo "Installing system dependencies..."
	sudo apt-get update
	sudo apt-get install -y portaudio19-dev python3-pyaudio
	@echo "Setting up Python virtual environment..."
	python3 -m venv .venv
	@echo "Installing dependencies..."
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -e .
	@echo "Setup complete. Activate venv with: source .venv/bin/activate"

# Build Docker images
build: ## Build consolidated Docker image using Buildx
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name voice-ai-builder 2>/dev/null || docker buildx use voice-ai-builder || true
	@echo "Building consolidated Voice AI Docker image..."
	docker buildx build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest --load --progress=plain .
	@echo "Docker image built successfully."

# Build with cache
build-cache: ## Build Docker images with BuildKit cache
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name voice-ai-builder 2>/dev/null || docker buildx use voice-ai-builder || true
	@echo "Building consolidated Voice AI Docker image with cache..."
	docker buildx build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest --load --progress=plain --cache-from type=local,src=/tmp/.buildx-cache-voice-ai --cache-to type=local,dest=/tmp/.buildx-cache-voice-ai-new,mode=max .
	@echo "Moving cache directories..."
	@mv /tmp/.buildx-cache-voice-ai-new /tmp/.buildx-cache-voice-ai 2>/dev/null || true
	@echo "Docker image built with cache successfully."

# Build for multiple platforms
build-multi: ## Build Docker images for multiple platforms
	@echo "Setting up Docker Buildx builder..."
	docker buildx create --use --name voice-ai-builder-multi 2>/dev/null || docker buildx use voice-ai-builder-multi || true
	@echo "Building consolidated Voice AI Docker image for multiple platforms..."
	docker buildx build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest --platform linux/amd64,linux/arm64 --push .
	@echo "Multi-platform Docker image built successfully."

# Build Docker images using Kubernetes Job
build-k8s: ## Build Docker images using Kubernetes Job (requires Docker socket access)
	@echo "Setting up Kubernetes image builder..."
	kubectl create namespace voice-ai-build --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -f k8s/kaniko-job.yaml
	@echo "Waiting for image build job to complete..."
	kubectl wait --for=condition=complete --timeout=600s job/voice-ai-image-builder -n voice-ai-build
	@echo "Image build completed. Loading into Minikube..."
	minikube image load voice-ai-pipeline:latest
	@echo "Cleaning up build job..."
	kubectl delete -f k8s/kaniko-job.yaml --ignore-not-found=true
	@echo "Kubernetes image build completed successfully."

# Deploy to Kubernetes
deploy: ## Deploy the application to Kubernetes
	@echo "Applying consolidated Kubernetes manifest..."
	kubectl apply -f k8s/voice-ai-deployment.yaml
	@echo "Waiting for deployment to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/voice-ai-deployment
	@echo "Deployment complete. Get service IP with: kubectl get svc voice-ai-service"

# Clean up resources
clean: ## Clean up Docker images and Kubernetes resources
	@echo "Deleting consolidated Kubernetes resources..."
	kubectl delete -f k8s/voice-ai-deployment.yaml --ignore-not-found=true
	@echo "Removing Docker images..."
	docker rmi voice-ai-pipeline:latest --force 2>/dev/null || true
	@echo "Cleaning up Docker Buildx builder..."
	docker buildx rm voice-ai-builder 2>/dev/null || true
	@echo "Cleaning up temporary files..."
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete."

# Run in development mode (local services)
dev: ## Run services locally for development
	@echo "Starting ASR service..."
	./.venv/bin/python -m voice_ai_pipeline.asr &
	@echo "Starting TTS service..."
	./.venv/bin/python -m voice_ai_pipeline.tts &
	@echo "Starting Interface..."
	./.venv/bin/python -m voice_ai_pipeline.interface &
	@echo "Services started. Access interface at http://localhost:7860"
	@echo "Stop with: pkill -f 'python -m voice_ai_pipeline'"

# Run optimization scripts
optimize: ## Run model optimization scripts
	@echo "Running ASR optimization..."
	./.venv/bin/python -m voice_ai_pipeline.optimize_asr
	@echo "Running TTS optimization..."
	./.venv/bin/python -m voice_ai_pipeline.optimize_tts

# Lint code
lint: ## Run linting on Python code
	@echo "Running flake8..."
	./.venv/bin/pip install flake8
	./.venv/bin/flake8 voice_ai_pipeline/ --max-line-length=100
	@echo "Linting complete."

# Format code
format: ## Format Python code with black
	@echo "Running black formatter..."
	./.venv/bin/pip install black
	./.venv/bin/black voice_ai_pipeline/
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
	pkill -f "python -m voice_ai_pipeline" || true
	@echo "Services stopped."

# Run comprehensive pipeline tests
test: ## Run comprehensive tests on all pipeline components
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Running pipeline tests..."
	./.venv/bin/python -m voice_ai_pipeline.tests.test_pipeline

# Run tests with verbose output
test-verbose: ## Run tests with detailed output
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Running pipeline tests with verbose output..."
	python3 -u -m voice_ai_pipeline.tests.test_pipeline

# Test microphone functionality
test-microphone: ## Test microphone recording and ASR transcription
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Testing microphone functionality..."
	./.venv/bin/python -m voice_ai_pipeline.microphone --test

# List available audio devices
list-devices: ## List available microphone devices
	@echo "Installing test dependencies..."
	./.venv/bin/pip install -r requirements_test.txt
	@echo "Listing available audio devices..."
	./.venv/bin/python -m voice_ai_pipeline.microphone --list-devices

# Kubernetes Testing Targets

# Run full Kubernetes test suite
test-k8s-full: ## Run complete Kubernetes test suite (setup + deploy + test)
	@echo "Running full Kubernetes test suite..."
	./scripts/test-k8s.sh full

# Run quick Kubernetes tests (assumes deployment exists)
test-k8s-quick: ## Run Kubernetes tests only (deployment must exist)
	@echo "Running quick Kubernetes tests..."
	./scripts/test-k8s.sh quick

# Setup and deploy to Kubernetes
test-k8s-setup: ## Setup and deploy to Kubernetes
	@echo "Setting up and deploying to Kubernetes..."
	./scripts/test-k8s.sh setup

# Run Kubernetes tests only
test-k8s-test: ## Run Kubernetes tests only
	@echo "Running Kubernetes tests..."
	./scripts/test-k8s.sh test

# Clean up Kubernetes resources
test-k8s-cleanup: ## Clean up Kubernetes resources
	@echo "Cleaning up Kubernetes resources..."
	./scripts/test-k8s.sh cleanup

# Setup port forwarding for local testing
test-k8s-port-forward: ## Setup port forwarding for local Kubernetes testing
	@echo "Setting up port forwarding..."
	./scripts/test-k8s.sh port-forward

# Show Kubernetes service URLs
test-k8s-urls: ## Show Kubernetes service URLs
	@echo "Getting service URLs..."
	./scripts/test-k8s.sh urls

# Test Kubernetes with Minikube
test-k8s-minikube: ## Run Kubernetes tests with Minikube
	@echo "Running Kubernetes tests with Minikube..."
	K8S_PROVIDER=minikube ./scripts/test-k8s.sh full

# Test Kubernetes deployment health
test-k8s-health: ## Test Kubernetes deployment health and connectivity
	@echo "Testing Kubernetes deployment health..."
	kubectl get pods -o wide
	@echo ""
	kubectl get svc -o wide
	@echo ""
	kubectl get deployments -o wide
	@echo ""
	@echo "Testing service endpoints..."
	./scripts/test-k8s.sh urls

# Kubernetes Management Targets

# Setup Kubernetes cluster and deploy resources
k8s-setup: ## Setup Kubernetes cluster and deploy application
	@echo "Setting up Kubernetes cluster..."
	@if ! kubectl cluster-info >/dev/null 2>&1; then \
		echo "Starting Minikube..."; \
		minikube start --driver=docker --gpus=all; \
		echo "Waiting for cluster to be ready..."; \
		kubectl wait --for=condition=Ready node/minikube --timeout=300s; \
	else \
		echo "Kubernetes cluster already running."; \
	fi
	@echo "Building Docker images..."
	$(MAKE) build
	@echo "Loading image into Minikube..."
	minikube image load voice-ai-pipeline:latest
	@echo "Applying consolidated Kubernetes manifest..."
	kubectl apply -f k8s/voice-ai-deployment.yaml
	@echo "Waiting for deployments to be ready..."
	kubectl wait --for=condition=available --timeout=300s deployment/voice-ai-deployment || (echo "Voice AI deployment failed. Check pod logs."; kubectl logs -l app=voice-ai --tail=50; exit 1)
	@echo "Kubernetes setup complete. Get service IP with: make k8s-urls"

# Clean up Kubernetes resources
k8s-cleanup: ## Clean up Kubernetes resources and optionally stop cluster
	@echo "Deleting consolidated Kubernetes resources..."
	kubectl delete -f k8s/voice-ai-deployment.yaml --ignore-not-found=true
	@echo "Waiting for resources to be deleted..."
	kubectl wait --for=delete deployment/voice-ai-deployment --timeout=60s || true
	@echo "Kubernetes resources cleaned up."

# Stop Kubernetes cluster
k8s-stop: ## Stop the Kubernetes cluster (Minikube)
	@echo "Stopping Kubernetes cluster..."
	minikube stop
	@echo "Cluster stopped."

# Show Kubernetes service URLs
k8s-urls: ## Show Kubernetes service URLs and access information
	@echo "Getting service information..."
	@echo "Voice AI Service:"
	kubectl get svc voice-ai-service -o jsonpath='{.spec.type} type, external IP: {.status.loadBalancer.ingress[0].ip}, ports: {.spec.ports[*].port}' 2>/dev/null || kubectl get svc voice-ai-service
	@echo ""
	@echo "Pod status:"
	kubectl get pods -o wide
	@echo ""
	@echo "To access the interface, use the LoadBalancer IP or set up port forwarding:"
	@echo "kubectl port-forward svc/voice-ai-service 7860:7860"
	@echo ""
	@echo "Service URLs:"
	@echo "  Interface: http://<EXTERNAL_IP>:7860"
	@echo "  ASR: http://<EXTERNAL_IP>:8000"
	@echo "  TTS: http://<EXTERNAL_IP>:8001"

# Check Kubernetes cluster status
k8s-status: ## Check Kubernetes cluster and deployment status
	@echo "Cluster status:"
	kubectl cluster-info
	@echo ""
	@echo "Node status:"
	kubectl get nodes
	@echo ""
	@echo "Pod status:"
	kubectl get pods
	@echo ""
	@echo "Service status:"
	kubectl get svc
	@echo ""
	@echo "Deployment status:"
	kubectl get deployments
