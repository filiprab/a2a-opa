FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project files
COPY pyproject.toml .
COPY requirements.txt .

# Install Python dependencies with uv
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY . .

# Install a2a-opa in development mode
RUN uv pip install --system -e ../../

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:9999/.well-known/agent.json || exit 1

# Expose port
EXPOSE 9999

# Start the application
CMD ["python", "main.py"]