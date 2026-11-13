FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/app.py /app/app.py
COPY src/templates /app/templates

EXPOSE 8080
CMD ["python", "app.py"]
