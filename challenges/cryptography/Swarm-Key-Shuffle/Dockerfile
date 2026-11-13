FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/main.py /app/main.py

RUN useradd --system --uid 10001 relay
USER relay

EXPOSE 31337

CMD ["python", "-u", "/app/main.py"]
