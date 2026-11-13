# Poisoned Telemetry app -- talks to an OpenAI-compatible model endpoint
# (LLM_BASE_URL); runs no model itself. The flag is injected at RUNTIME
# (-e FLAG=...), never baked in.
FROM python:3.12-slim

ENV HOME=/tmp PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY src/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./

# drop privileges (defense in depth); /data holds the GM transcript log
RUN useradd -r -u 10001 ctf && mkdir -p /data && chown -R ctf:ctf /app /data
USER ctf

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]
