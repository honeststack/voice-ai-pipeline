# Multi-stage build for consolidated AI services
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu22.04 AS builder

# Add metadata labels
LABEL maintainer="TTS AI Pipeline Team" \
      description="Consolidated ASR and TTS services" \
      version="2.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements_asr.txt requirements_tts.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_asr.txt -r requirements_tts.txt

# Production stage
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu22.04

# Add metadata labels
LABEL maintainer="TTS AI Pipeline Team" \
      description="Consolidated ASR and TTS services" \
      version="2.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && mkdir -p /app \
    && chown -R app:app /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=app:app voice_ai_pipeline/ /app/voice_ai_pipeline/

# Copy interface code (assuming it's in the same repo)
COPY --chown=app:app . /app/

# Set working directory
WORKDIR /app

# Switch to non-root user
USER app

# Expose ports
EXPOSE 8000 8001 7860

# Health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health && curl -f http://localhost:8001/health && curl -f http://localhost:7860/ || exit 1

# Start all services
CMD ["sh", "-c", "\
    echo 'Starting ASR service...' && \
    SERVICE_TYPE=asr PORT=8000 python3 -m voice_ai_pipeline.asr & \
    echo 'Starting TTS service...' && \
    SERVICE_TYPE=tts PORT=8001 python3 -m voice_ai_pipeline.tts & \
    echo 'Starting Interface service...' && \
    python3 -m voice_ai_pipeline.interface & \
    echo 'All services started. Waiting...' && \
    wait"]
