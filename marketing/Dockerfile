FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY docs ./docs
COPY marketing ./marketing
RUN pip install --no-cache-dir .
RUN mkdir -p /data
ENV KIZUNA_MARKETING_DATA_DIR=/data
EXPOSE 8080
HEALTHCHECK --interval=20s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"
CMD ["uvicorn", "marketing.main:app", "--host", "0.0.0.0", "--port", "8080"]
