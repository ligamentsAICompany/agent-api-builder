# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Install git (required for git operations in the backend)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy the backend requirements first to leverage Docker cache
COPY backend/requirements.txt ./backend/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the rest of the application code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create directories for generated content
RUN mkdir -p generated_apis git_repos

# Make port 5001 available to the world outside this container
EXPOSE 5001

# Define environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backend/server.py

# Run server.py when the container launches
CMD ["python", "backend/server.py"]
