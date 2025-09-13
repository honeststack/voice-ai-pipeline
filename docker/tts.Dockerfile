# TTS Service Dockerfile
FROM nvidia/cuda:13.0.1-cudnn-runtime-ubuntu22.04

# Add metadata labels
LABEL maintainer="TTS AI Pipeline Team" \
      description="TTS Service using Coqui TTS for text-to-speech synthesis" \
      version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app \
    && chown -R app:app /app

# Set working directory
WORKDIR /app

# Switch to non-root user
USER app

# Copy requirements first for better caching
COPY --chown=app:app requirements_tts.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements_tts.txt

# Copy application code
COPY --chown=app:app tts_ai_pipeline/tts.py .

# Add Python user bin to PATH
ENV PATH="/home/app/.local/bin:$PATH"

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["python3", "-m", "tts"]
