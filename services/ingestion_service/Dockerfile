# Use Python 3.12 slim image
FROM python:3.14-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for:
# - psycopg (PostgreSQL driver): libpq-dev
# - Building Python packages: gcc
# - Health check: curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker caches this layer)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8001 for the ingestion API
EXPOSE 8001

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

