# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
ENV NODE_MAJOR=20
ENV PYTHONUNBUFFERED=1
# Increase gunicorn timeout and request body limit for large uploads
ENV GUNICORN_CMD_ARGS="--timeout 600 --limit-request-body 1073741824"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    unzip \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install NodeJS
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - && \
    apt-get install -y nodejs

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Final cleanup of any potential leftover build files
RUN rm -rf .web

# Initialize the Reflex project
# This creates the .web directory and installs frontend dependencies
RUN reflex init

# Link the assets directory to the frontend's public folder
# This ensures both static and dynamic assets (favicon, processed images) 
# are served correctly by the static frontend server at runtime.
RUN rm -rf .web/public && ln -s /app/assets /app/.web/public

# Expose the ports for the frontend (3002) and backend (8002)
EXPOSE 3002 8002

# Default command: run in production mode
# Use --env prod to optimize the frontend build
CMD ["reflex", "run", "--env", "prod", "--frontend-port", "3002", "--backend-port", "8002"]
