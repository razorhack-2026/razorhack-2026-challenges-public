FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY static ./static

EXPOSE 8080
# One worker: round state lives in memory, shared across threads. /dev/shm because the root fs is read-only.
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--threads", "8", "--worker-tmp-dir", "/dev/shm", "app:app"]
