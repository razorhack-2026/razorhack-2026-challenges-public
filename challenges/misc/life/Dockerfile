FROM python:3.12-slim
WORKDIR /app
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/app.py .
EXPOSE 8081
CMD ["gunicorn", "-b", "0.0.0.0:8081", "app:app"]
