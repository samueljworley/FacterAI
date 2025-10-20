# Dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall -y boto3 botocore s3transfer awscli aioboto3 aiobotocore || true


# System deps (build tools for some libs)
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better caching)
COPY requirements.txt .

# Copy the app
COPY . .

# Gunicorn will serve the WSGI app
ENV PORT=8080 PYTHONUNBUFFERED=1
CMD ["gunicorn","-k","gthread","--workers","1","--threads","4","--timeout","60","--bind","0.0.0.0:8080","--log-level","info","--access-logfile","-","--error-logfile","-","wsgi:app"]
