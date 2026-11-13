FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "pymodbus>=3.8.0"

COPY server.py coordinates.json ./

EXPOSE 502

CMD ["python", "server.py", "--port", "502"]
