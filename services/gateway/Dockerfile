# Use a consistent Python version with other backend services
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies. 'curl' is needed for the health check.
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker's layer caching
COPY services/gateway/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Now copy the rest of the application code
COPY shared /app/shared
COPY services/gateway .

# The logs directory is kept for consistency if your code writes to files.
# Logging to stdout is standard for containers.
RUN mkdir -p /app/logs

# Expose the port the application will run on inside the container.
# This MUST match the port in the HEALTHCHECK and CMD instructions.
EXPOSE 8080

# Add a health check to ensure the service is running and responsive.
# Docker Compose will wait for this check to pass.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# The command to run the Uvicorn server for FastAPI.
# We use port 8080 to match the new port mapping in docker-compose.yml.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]