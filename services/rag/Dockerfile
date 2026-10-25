FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY services/rag/requirements.txt requirements.txt
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY services /app/services
COPY corpus /app/corpus

ENV PYTHONPATH=/app
EXPOSE 8003

CMD ["uvicorn", "services.rag.main:app", "--host", "0.0.0.0", "--port", "8003"]
