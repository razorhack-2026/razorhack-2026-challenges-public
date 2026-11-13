FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# colony.txt lives here too — it is the starting board the server validates removals against. The removal set is the answer key and must never be COPYed into dist/. The service keeps it server-side only.
COPY src/app.py /app/app.py
COPY src/ringlife.py /app/ringlife.py
COPY src/colony.txt /app/colony.txt
COPY src/index.html /app/index.html

EXPOSE 40818
CMD ["python", "app.py"]
