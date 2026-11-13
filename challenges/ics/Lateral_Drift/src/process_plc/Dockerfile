FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config.py process_plc.py ./
EXPOSE 502 8000
CMD ["python", "-u", "process_plc.py"]
