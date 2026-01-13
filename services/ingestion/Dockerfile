# Use a consistent Python version with other backend services
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies. 'curl' is needed for the health check.
# 'gcc' and 'g++' are often required for compiling certain Python packages.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker's layer caching
COPY services/ingestion/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Now copy the rest of the application code
COPY shared /app/shared
COPY services/ingestion .

# Create directories for logs and uploads.
# The 'uploads' directory is important if you plan to temporarily store files,
# though it's often better to handle them in memory or cloud storage.
RUN mkdir -p /app/logs
RUN mkdir -p /app/uploads

# Expose the port the application will run on inside the container.
# This MUST match the port in the HEALTHCHECK and CMD instructions.
EXPOSE 8000

# Add a health check to ensure the service is running and responsive.
# Docker Compose will wait for this check to pass.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# The command to run the Uvicorn server for FastAPI.
# This is the standard way to run a FastAPI app in production.
# We use port 8000 to match our port mapping in docker-compose.yml.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]