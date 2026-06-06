# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies for Playwright/Camoufox
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    supervisor \
    libpq-dev \
    gcc \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install firefox
RUN playwright install-deps firefox

# Copy project files
COPY . /app/

# Create log files for supervisor
RUN touch /var/log/redis.log /var/log/redis.err \
    /var/log/flask.log /var/log/flask.err \
    /var/log/celery-worker.log /var/log/celery-worker.err \
    /var/log/celery-beat.log /var/log/celery-beat.err

# Expose the Flask port
EXPOSE 5000

# Start supervisor to manage all processes
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
