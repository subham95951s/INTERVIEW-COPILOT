FROM python:3.12-slim

WORKDIR /app

# System dependencies for audio processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Silero VAD model at build time (fix.md Gap 1.1)
# torch.hub.load() downloads from GitHub — must happen during build,
# not at runtime when the container may have no internet access.
RUN python -c "\
import torch; \
torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=True, onnx=False); \
print('Silero VAD model cached successfully')"

# Copy application code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
