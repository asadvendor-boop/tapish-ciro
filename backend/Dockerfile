FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Firebase credentials: Cloud Run uses service identity automatically.
# For local dev, set GOOGLE_APPLICATION_CREDENTIALS env var.
# DO NOT bake service account keys into the image.

# Copy application code
COPY app/ ./app/

# Copy web dashboard
COPY web/ ./web/

# Create TTS output directory
RUN mkdir -p /app/tts_output

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV FIREBASE_CREDENTIALS_PATH=""
ENV GOOGLE_CLOUD_PROJECT=tapish-crisis

# Expose Cloud Run port
EXPOSE 8080

# Run the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
