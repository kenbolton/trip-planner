FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 kayakbot

# Copy application code
COPY --chown=kayakbot:kayakbot . .

# Create directories for data and logs with proper ownership
RUN mkdir -p /app/data /app/logs && \
    chown -R kayakbot:kayakbot /app

USER kayakbot

# Expose health check port (optional)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python health_check.py || exit 1

# Run the bot
CMD ["python", "bot.py"]
