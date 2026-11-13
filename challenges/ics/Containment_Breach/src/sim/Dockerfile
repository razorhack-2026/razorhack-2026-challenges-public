FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port 502 is the standard Modbus/TCP port.
# The container runs as root (default), so binding < 1024 works without extra caps.
EXPOSE 502 503 504 505 5030

# -u: unbuffered stdout so logs appear immediately in `docker compose logs`.
CMD ["python", "-u", "containment_sim.py"]
