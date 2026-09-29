FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*

RUN curl -L -o /tmp/opa \
    https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static \
    && chmod +x /tmp/opa \
    && mv /tmp/opa /usr/local/bin/opa

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

ENTRYPOINT []
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]