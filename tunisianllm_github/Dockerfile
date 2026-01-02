# NVIDIA CUDA 12.1 base (matches pytorch-cuda=12.1)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (ffmpeg for pydub, Python 3.10, git, etc.)
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy project files FIRST (for better Docker layer caching)
COPY requirements.txt environment.yml ./
COPY api/ ./api/
COPY vosk-model/ ./vosk-model/
COPY TunCHAT-V0.2/ ./TunCHAT-V0.2/

# Install Python dependencies from requirements.txt + conda-like packages
RUN pip install --no-cache-dir --upgrade pip
# Core ML stack (matches your pytorch-cuda=12.1)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# FastAPI + API deps
RUN pip install -r requirements.txt
# Quantization + accelerate (critical for your 4-bit setup)
RUN pip install bitsandbytes accelerate transformers

# Create offload directory
RUN mkdir -p tmp_offload

# Expose port 8005
EXPOSE 8005

# Health check (optional)
HEALTHCHECK CMD curl -f http://localhost:8005/health || exit 1

# Run your exact FastAPI app
CMD ["python", "-m", "uvicorn", "api.api_tunisianllm:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]