# Dockerfile for Telegram Bot - Cloud Optimized
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set cloud environment variable
ENV RAILWAY_ENVIRONMENT=true

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    traceroute \
    whois \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with timeout and retry
RUN pip install --no-cache-dir --timeout=300 --retries=3 -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port (if needed for health checks)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run the bot
CMD ["python", "bot.py"]