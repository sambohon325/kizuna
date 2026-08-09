FROM python:3.13-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY app ./app
COPY scanner ./scanner
COPY alembic.ini ./
COPY migrations ./migrations
COPY node_agent ./node_agent
RUN pip install --no-cache-dir . psycopg[binary]>=3.2,<4
RUN mkdir -p /app/renders /app/storage
EXPOSE 8000 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
