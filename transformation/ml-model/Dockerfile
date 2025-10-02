# Transformation Pipeline Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY ml-model/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy SQL transformation files
COPY sql ./sql

# Copy transformation script
COPY ml-model/main.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run transformation pipeline
CMD ["python", "-u", "main.py"]
