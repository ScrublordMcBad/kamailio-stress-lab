FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (to trigger SIPp containers)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY sip_client.py .
COPY templates/ templates/

EXPOSE 5000

CMD ["python3", "app.py"]
