# Use Python 3.12 slim image (smaller than full image)
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
# Changes to code won't trigger reinstall of dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for the API
EXPOSE 8000

# Command to run the application
# --host 0.0.0.0 makes it accessible from outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

