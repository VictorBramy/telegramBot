# Dockerfile for Telegram Bot - Ultra Stable Cloud Version
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set cloud environment variable
ENV RAILWAY_ENVIRONMENT=true
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with conservative settings
RUN pip install --no-cache-dir --timeout=600 --retries=5 -r requirements.txt || \
    pip install --no-cache-dir python-telegram-bot python-dotenv requests

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