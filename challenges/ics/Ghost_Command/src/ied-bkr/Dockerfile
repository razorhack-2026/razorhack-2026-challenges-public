# Build context is src/ (see docker-compose.yml) so this can pull in the
# shared GOOSE codec from common/.
FROM python:3.12-slim

WORKDIR /app

COPY ied-bkr/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY ied-bkr/main.py .

EXPOSE 502

CMD ["python", "main.py"]
