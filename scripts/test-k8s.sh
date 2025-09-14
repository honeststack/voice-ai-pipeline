#!/bin/bash
# Kubernetes Test Runner Script
# This script provides utilities for running comprehensive Kubernetes tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${K8S_NAMESPACE:-default}"
TIMEOUT="${K8S_TIMEOUT:-300}"
RETRY_COUNT="${K8S_RETRY_COUNT:-3}"

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if kubectl is available and configured
check_kubectl() {
    log "Checking kubectl configuration..."

    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        info "Install kubectl with:"
        info "  curl -LO \"https://dl.k8s.io/release/\$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl\""
        info "  sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl"
        exit 1
    fi

    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        info "Please start a Kubernetes cluster first:"
        info "  - For local testing: minikube start --driver=docker --gpus=all"
        info "  - For cloud clusters: configure kubectl for your cluster"
        info ""
        info "Or run with K8S_PROVIDER=minikube to auto-start minikube:"
        info "  K8S_PROVIDER=minikube $0 full"
        exit 1
    fi

    success "kubectl is configured and connected to cluster"
}

# Check if required tools are available
check_dependencies() {
    log "Checking dependencies..."

    local missing_deps=()

    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi

    if ! command -v minikube &> /dev/null && [[ "$K8S_PROVIDER" == "minikube" ]]; then
        missing_deps+=("minikube")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing_deps[*]}"
        info "Please install missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            case $dep in
                "docker")
                    info "  Docker: https://docs.docker.com/get-docker/"
                    ;;
                "minikube")
                    info "  Minikube: https://minikube.sigs.k8s.io/docs/start/"
                    ;;
            esac
        done
        exit 1
    fi

    # Check if Docker is running
    if ! docker info &> /dev/null; then
        error "Docker is not running"
        info "Please start Docker:"
        info "  sudo systemctl start docker  # Linux"
        info "  # Or start Docker Desktop on macOS/Windows"
        exit 1
    fi

    # Check if Docker Buildx is available
    if ! docker buildx version &> /dev/null; then
        error "Docker Buildx is not available"
        info "Please install Docker Buildx:"
        info "  - For Docker Desktop: Buildx is included by default"
        info "  - For Linux: Follow https://docs.docker.com/engine/install/linux-postinstall/"
        info "  - Or install manually: https://github.com/docker/buildx#installing"
        exit 1
    fi

    success "All dependencies are available"
}

# Setup Minikube if specified
setup_minikube() {
    if [[ "$K8S_PROVIDER" == "minikube" ]]; then
        log "Setting up Minikube..."

        if ! minikube status &> /dev/null; then
            info "Starting Minikube..."
            minikube start --driver=docker --cpus=2 --memory=4096 --gpus=all
        fi

        # Enable ingress if needed
        minikube addons enable ingress

        success "Minikube is ready"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."

    # Check if consolidated Dockerfile exists
    if [[ ! -f "docker/asr.Dockerfile" ]]; then
        error "Consolidated Dockerfile not found: docker/asr.Dockerfile"
        exit 1
    fi

    # Set up Docker Buildx builder
    info "Setting up Docker Buildx builder..."

    # Create and use buildx builder
    if ! docker buildx create --use --name voice-ai-builder 2>/dev/null; then
        # Builder might already exist, try to use it
        if ! docker buildx use voice-ai-builder 2>/dev/null; then
            warning "Could not create/use voice-ai-builder, using default builder"
        fi
    fi

    # Build consolidated Voice AI image
    info "Building consolidated Voice AI image with Buildx..."
    if ! docker buildx build -f docker/asr.Dockerfile -t voice-ai-pipeline:latest --load --progress=plain .; then
        error "Failed to build consolidated Voice AI image with Buildx"
        exit 1
    fi

    success "Consolidated Voice AI Docker image built successfully with Buildx"
}

# Load images into Minikube if using Minikube
load_images_minikube() {
    if [[ "$K8S_PROVIDER" == "minikube" ]]; then
        log "Loading images into Minikube..."

        # Check if minikube is running
        if ! minikube status &> /dev/null; then
            error "Minikube is not running"
            info "Please start minikube first: minikube start --driver=docker --gpus=all"
            exit 1
        fi

        # Load consolidated image
        if ! minikube image load voice-ai-pipeline:latest; then
            error "Failed to load consolidated Voice AI image into Minikube"
            exit 1
        fi

        success "Consolidated Voice AI image loaded into Minikube"
    fi
}

# Deploy to Kubernetes
deploy_k8s() {
    log "Deploying to Kubernetes..."

    # Check if k8s directory exists
    if [[ ! -d "k8s" ]]; then
        error "Kubernetes manifests directory not found: k8s/"
        exit 1
    fi

    # Check for required manifests
    local required_manifests=("voice-ai-deployment.yaml")
    for manifest in "${required_manifests[@]}"; do
        if [[ ! -f "k8s/$manifest" ]]; then
            error "Required manifest not found: k8s/$manifest"
            exit 1
        fi
    done

    # Apply all manifests
    info "Applying Kubernetes manifests..."
    if ! kubectl apply -f k8s/; then
        error "Failed to apply Kubernetes manifests"
        exit 1
    fi

    # Wait for deployment to be ready
    info "Waiting for deployment to be ready..."
    if ! kubectl wait --for=condition=available --timeout=${TIMEOUT}s deployment/voice-ai-deployment; then
        error "Voice AI deployment failed to become ready"
        exit 1
    fi

    success "Deployment completed successfully"
}

# Run comprehensive tests
run_tests() {
    log "Running comprehensive Kubernetes tests..."

    # Check if test module exists
    if [[ ! -f "voice_ai_pipeline/tests/test_k8s.py" ]]; then
        error "Test module not found: voice_ai_pipeline/tests/test_k8s.py"
        exit 1
    fi

    # Run the Python test suite
    info "Running Python test suite..."
    if ! python -m voice_ai_pipeline.tests.test_k8s; then
        error "Python test suite failed"
        exit 1
    fi

    success "Test suite completed"
}

# Get service URLs
get_service_urls() {
    log "Getting service URLs..."

    # Voice AI service (consolidated)
    local voice_ai_url=$(kubectl get svc voice-ai-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "localhost")
    info "Voice AI Service: http://${voice_ai_url}:7860 (Interface)"
    info "ASR Service: http://${voice_ai_url}:8000"
    info "TTS Service: http://${voice_ai_url}:8001"
}

# Cleanup resources
cleanup() {
    log "Cleaning up Kubernetes resources..."

    kubectl delete -f k8s/ --ignore-not-found=true

    if [[ "$K8S_PROVIDER" == "minikube" ]]; then
        info "Cleaning up Minikube..."
        minikube delete
    fi

    success "Cleanup completed"
}

# Setup port forwarding for local testing
setup_port_forwarding() {
    log "Setting up port forwarding for local testing..."

    # Get pod names
    local asr_pod=$(kubectl get pods -l app=asr -o jsonpath='{.items[0].metadata.name}')
    local tts_pod=$(kubectl get pods -l app=tts -o jsonpath='{.items[0].metadata.name}')
    local interface_pod=$(kubectl get pods -l app=interface -o jsonpath='{.items[0].metadata.name}')

    # Start port forwarding in background
    info "Starting port forwarding..."
    kubectl port-forward pod/${asr_pod} 8000:8000 &
    ASR_PF_PID=$!

    kubectl port-forward pod/${tts_pod} 8001:8001 &
    TTS_PF_PID=$!

    kubectl port-forward pod/${interface_pod} 7860:7860 &
    INTERFACE_PF_PID=$!

    success "Port forwarding established"
    info "ASR: http://localhost:8000"
    info "TTS: http://localhost:8001"
    info "Interface: http://localhost:7860"
    info "Press Ctrl+C to stop port forwarding"

    # Wait for port forwarding
    wait
}

# Main functions
run_full_test() {
    log "🚀 Starting Full Kubernetes Test Suite"
    echo "========================================"

    check_kubectl
    check_dependencies
    setup_minikube
    # build_images
    load_images_minikube
    deploy_k8s
    get_service_urls
    run_tests

    success "🎉 Full test suite completed successfully!"
}

run_quick_test() {
    log "⚡ Starting Quick Kubernetes Test"
    echo "=================================="

    check_kubectl
    run_tests

    success "Quick test completed!"
}

# Command line interface
case "${1:-help}" in
    "full")
        run_full_test
        ;;
    "quick")
        run_quick_test
        ;;
    "setup")
        check_kubectl
        check_dependencies
        setup_minikube
        build_images
        load_images_minikube
        deploy_k8s
        ;;
    "test")
        check_kubectl
        run_tests
        ;;
    "cleanup")
        cleanup
        ;;
    "port-forward")
        check_kubectl
        setup_port_forwarding
        ;;
    "urls")
        check_kubectl
        get_service_urls
        ;;
    "help"|*)
        echo "Kubernetes Test Runner"
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  full         - Run complete test suite (setup + deploy + test)"
        echo "  quick        - Run tests only (assumes deployment exists)"
        echo "  setup        - Setup and deploy to Kubernetes"
        echo "  test         - Run tests only"
        echo "  cleanup      - Clean up all resources"
        echo "  port-forward - Setup port forwarding for local testing"
        echo "  urls         - Show service URLs"
        echo "  help         - Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  K8S_NAMESPACE    - Kubernetes namespace (default: default)"
        echo "  K8S_TIMEOUT      - Timeout for operations (default: 300s)"
        echo "  K8S_RETRY_COUNT  - Retry count for operations (default: 3)"
        echo "  K8S_PROVIDER     - Kubernetes provider (minikube, etc.)"
        ;;
esac
