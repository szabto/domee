FROM python:3.12-slim

LABEL org.opencontainers.image.title="Domee"
LABEL org.opencontainers.image.description="Self-hosted domain availability checker with watchlist and email notifications"
LABEL org.opencontainers.image.source="https://github.com/szabto/domee"
LABEL org.opencontainers.image.licenses="MIT"

# Install whois client (needed by python-whois)
RUN apt-get update && \
    apt-get install -y --no-install-recommends whois && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

ENV DOMEE_DB_PATH=/data/domee.db

EXPOSE 8000

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/settings')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
