FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -m ctf
COPY src/server.py .
COPY src/static/ ./static/
USER ctf
ENV PORT=8000 TIME_LIMIT=30
EXPOSE 8000
CMD ["python3", "server.py"]
