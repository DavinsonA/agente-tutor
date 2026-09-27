FROM python:3.11-slim

ARG TECTONIC=0.15.0
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC}/tectonic-${TECTONIC}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C /usr/local/bin \
    && apt-get purge -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip install --no-cache-dir flask
COPY app.py .
RUN python -c "import app; app.precalentar()"

EXPOSE 5001
CMD ["python", "app.py"]
