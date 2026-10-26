FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy ML inference code and trained model artifacts (training datasets excluded)
COPY ml/__init__.py /app/ml/__init__.py
COPY ml/training/ /app/ml/training/
COPY ml/artifacts/ /app/ml/artifacts/

ENV PYTHONPATH="/app"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
