# Consolidated Voice AI Pipeline
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu22.04

# Add metadata labels
LABEL maintainer="TTS AI Pipeline Team" \
      description="Consolidated Voice AI Pipeline - ASR, TTS, and Interface services" \
      version="3.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app \
    SERVICE_TYPE=all

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    ffmpeg \
    curl \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements_*.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements_asr.txt -r requirements_tts.txt -r requirements_interface.txt -r requirements_test.txt && \
    rm -rf /root/.cache/pip/* && \
    rm -f requirements_*.txt
    
# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && mkdir -p /app \
    && chown -R app:app /app

# Copy application code
COPY --chown=app:app . /app/

# Clean up unnecessary files
RUN rm -rf /app/docker /app/k8s /app/scripts /app/tests /app/docs /app/*.md /app/Makefile /app/requirements*.txt \
    && find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /app -name "*.pyo" -delete \
    && find /app -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /app -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

# Set working directory
WORKDIR /app

# Switch to non-root user
USER app

# Expose ports
EXPOSE 8000 8001 7860

# Health checks for all services
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health && curl -f http://localhost:8001/health && curl -f http://localhost:7860/ || exit 1

# Start all services in parallel with proper async handling
CMD ["sh", "-c", "\
    echo '🚀 Starting Voice AI Pipeline Services...' && \
    echo '📝 Starting ASR service on port 8000...' && \
    SERVICE_TYPE=asr PORT=8000 python3 -m voice_ai_pipeline.asr & \
    echo '🔊 Starting TTS service on port 8001...' && \
    SERVICE_TYPE=tts PORT=8001 python3 -m voice_ai_pipeline.tts & \
    echo '🌐 Starting Interface service on port 7860...' && \
    python3 -m voice_ai_pipeline.interface & \
    echo '✅ All services started successfully!' && \
    echo '📊 Service URLs:' && \
    echo '   - ASR: http://localhost:8000' && \
    echo '   - TTS: http://localhost:8001' && \
    echo '   - Interface: http://localhost:7860' && \
    echo '⏳ Waiting for services...' && \
    wait"]
