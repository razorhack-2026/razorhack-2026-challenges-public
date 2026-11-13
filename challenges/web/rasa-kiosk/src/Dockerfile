# Python version matches the project's .venv
FROM python:3.14-slim

# OpenCV needs libgl1 + libglib2.0-0 (insightface 2.x ships prebuilt, so no compiler needed).
# Retries help on slow or flaky networks.
RUN apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies before copying code so this layer is cached
COPY requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r requirements.txt

# InsightFace's buffalo_l face models (~300 MB) go into the image, where the app looks for them
# (~/.insightface), so a copy started at the event never downloads them. /data holds the SQLite
# file (--db below); compose mounts a volume there, a hosted copy starts with it empty.
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l', allowed_modules=['detection', 'recognition'], providers=['CPUExecutionProvider']).prepare(ctx_id=-1)" \
    && mkdir -p /data

COPY . .

EXPOSE 5000
CMD ["python", "app.py", "--host", "0.0.0.0", "--db", "/data/hackathon.db"]
