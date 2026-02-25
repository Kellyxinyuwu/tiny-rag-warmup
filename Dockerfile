# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system deps (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY requirements.txt pyproject.toml ./

# Copy source
COPY src/ ./src/

# Install dependencies and package
RUN pip install --no-cache-dir -r requirements.txt && pip install -e .

# Expose API port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "tiny_rag.api:app", "--host", "0.0.0.0", "--port", "8000"]
