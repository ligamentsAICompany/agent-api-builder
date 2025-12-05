# Deploying Auto API Builder to Google Cloud Platform (GCP)

This guide will help you containerize and deploy your application to Google Cloud Run.

## Prerequisites

1.  **Google Cloud Project**: A GCP project with billing enabled.
2.  **gcloud CLI**: Installed and authenticated (`gcloud auth login`).
3.  **Docker**: Installed and running.

## Step 1: Initialize Google Cloud SDK

Open your terminal and ensure you are connected to your project:

```bash
# Set your project ID
gcloud config set project [YOUR_PROJECT_ID]

# Enable necessary services
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com
```

## Step 2: Build and Push the Docker Image

You can build the image locally and push it, or use Cloud Build to build it directly in the cloud (recommended for faster uploads).

### Option A: Use Cloud Build (Recommended)

Run this command from the project root (`d:\workspace\AGENT-API-BUILDER\auto-api-generator`):

```bash
gcloud builds submit --tag gcr.io/[YOUR_PROJECT_ID]/auto-api-builder
```

Replace `[YOUR_PROJECT_ID]` with your actual GCP project ID.

### Option B: Build Locally and Push

```bash
# Build
docker build -t gcr.io/[YOUR_PROJECT_ID]/auto-api-builder .

# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Push
docker push gcr.io/[YOUR_PROJECT_ID]/auto-api-builder
```

## Step 3: Deploy to Cloud Run

Once the image is pushed, deploy it to Cloud Run:

```bash
gcloud run deploy auto-api-builder \
  --image gcr.io/[YOUR_PROJECT_ID]/auto-api-builder \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 5001 \
  --set-env-vars GROQ_API_KEY=[YOUR_KEY],OPENAI_API_KEY=[YOUR_KEY]
```

*   Replace `[YOUR_KEY]` with your actual API keys. You only need one of them.
*   The `--port 5001` flag is crucial because the application listens on port 5001.

## Step 4: Access Your Application

After deployment, Cloud Run will provide a URL (e.g., `https://auto-api-builder-xxxxx-uc.a.run.app`). 
Open this URL in your browser to use the application.

## Troubleshooting

-   **502 Bad Gateway**: Ensure the `--port 5001` flag was used. Cloud Run defaults to checking port 8080.
-   **API Errors**: Check the Cloud Run logs tab to see if there are Python errors or missing API keys.
-   **Git Errors**: If using Git features (Load/Push), ensure the container has internet access (default in Cloud Run) and consider using a GitHub Token for private repos.

## Local Testing with Docker

To test the container locally before deploying:

```bash
docker build -t auto-api-local .
docker run -p 5001:5001 -e GROQ_API_KEY=your_key_here auto-api-local
```

Access at `http://localhost:5001`.
