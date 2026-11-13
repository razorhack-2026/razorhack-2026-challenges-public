FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY system_prompt.py providers.py app.py ./
EXPOSE 8090
CMD ["python", "-u", "app.py"]
