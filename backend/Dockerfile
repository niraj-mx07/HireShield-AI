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

# Optional: contextual NLP NER providers (spaCy + en_core_web_sm + Transformers).
# Enable with:  docker build --build-arg INSTALL_NLP=true ...
# When omitted, app/services/nlp_entities.py degrades to regex-only entity
# extraction and page retrieval/detection features continue to work normally.
ARG INSTALL_NLP=false
COPY backend/requirements-nlp.txt ./requirements-nlp.txt
RUN if [ "$INSTALL_NLP" = "true" ]; then pip install --no-cache-dir -r requirements-nlp.txt; fi

# Copy backend application code
COPY backend/ ./

# Copy ML artifacts into position
COPY ml/artifacts/ /app/ml/artifacts/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
