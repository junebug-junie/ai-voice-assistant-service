# Use the official NVIDIA CUDA image as the single base for everything.
# This ensures all paths and dependencies are consistent.
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# Set the working directory
WORKDIR /app

# Install Python, pip, and other necessary tools into the Ubuntu base image
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies directly using the system's pip3.
# This avoids the "bad interpreter" error from copied venvs.
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port the application will run on
EXPOSE 8080

# The health check is disabled for now to ensure startup.
# HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
#  CMD curl --fail http://localhost:8080/health || exit 1

# Define the command to run the application using the system's python3 path.
# We use the full path to uvicorn to be explicit.
CMD ["/usr/local/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
