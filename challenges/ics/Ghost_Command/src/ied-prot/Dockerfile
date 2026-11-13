# Build context is src/ (see docker-compose.yml) so this can pull in the
# shared GOOSE codec from common/.
FROM python:3.12-slim

WORKDIR /app

COPY common /app/common
COPY ied-prot/publisher.py .

CMD ["python", "publisher.py"]
