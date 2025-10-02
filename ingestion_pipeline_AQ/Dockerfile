FROM mirror.gcr.io/library/python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN cat requirements.txt && pip install -v --no-cache-dir -r requirements.txt
COPY ingestion_openaq.py wrapper_debug.py ./
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "wrapper_debug.py"]
