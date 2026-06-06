# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    redis-server \
    supervisor \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

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
