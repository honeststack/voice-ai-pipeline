# Interface Service Dockerfile
FROM python:3.10-slim

# Add metadata labels
LABEL maintainer="TTS AI Pipeline Team" \
      description="Gradio Interface for TTS AI Pipeline" \
      version="1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
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
COPY --chown=app:app requirements_interface.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements_interface.txt

# Copy application code
COPY --chown=app:app voice_ai_pipeline/interface.py .

# Add Python user bin to PATH
ENV PATH="/home/app/.local/bin:$PATH"

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Run the application
CMD ["python3", "-m", "interface"]
