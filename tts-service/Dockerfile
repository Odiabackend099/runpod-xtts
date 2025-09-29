# Multi-stage Docker build for production TTS service
FROM python:3.9-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    espeak-ng \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    espeak-ng \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash tts

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create necessary directories
RUN mkdir -p voice_storage logs

# Set environment variables
ENV PYTHONPATH=/app
ENV TTS_AGREE_TO_CPML=1
ENV PYTHONUNBUFFERED=1

# Change ownership to non-root user
RUN chown -R tts:tts /app

# Switch to non-root user
USER tts

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Run the application
CMD ["python", "-m", "src.server"]
