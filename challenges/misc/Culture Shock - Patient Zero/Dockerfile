FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# target.txt lives here too — it is the answer key, so it must never be COPYed
# into dist/. The service keeps it server-side only.
COPY src/app.py /app/app.py
COPY src/ringlife.py /app/ringlife.py
COPY src/target.txt /app/target.txt
COPY src/index.html /app/index.html

EXPOSE 40817
CMD ["python", "app.py"]
