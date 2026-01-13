# Use a consistent Python version with other backend services
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies. 'build-essential' is often needed for compiling
# certain Python packages that have C extensions.
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker's layer caching.
# This layer will only be rebuilt if the requirements.txt file changes.
COPY services/auth/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Now copy the rest of the code.
# The shared directory contains common modules like database managers.
COPY shared /app/shared

# The service-specific code.
COPY services/auth /app/

# Expose the port the application will run on inside the container.
# This MUST match the port in the CMD instruction.
EXPOSE 8002

# Add a health check to ensure the service is running and responsive.
# Docker Compose will wait for this check to pass before starting dependent services.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# The command to run the Uvicorn server for FastAPI.
# We use port 8002 to match the new port mapping in docker-compose.yml.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]