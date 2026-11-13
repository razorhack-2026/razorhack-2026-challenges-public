FROM python:3.12-slim

WORKDIR /app
COPY src/ .
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home challenge
USER challenge

EXPOSE 8000
CMD [ "python", "main.py" ]