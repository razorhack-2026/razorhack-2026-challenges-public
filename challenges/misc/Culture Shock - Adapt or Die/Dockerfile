FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ringlife.py holds the growth law, which IS the answer. It stays server-side
# and is never shipped in dist/. The page in index.html contains no simulation
# code: it posts boards to /observe and draws what comes back.
COPY src/app.py /app/app.py
COPY src/ringlife.py /app/ringlife.py
COPY src/specimen.txt /app/specimen.txt
COPY src/clips.json /app/clips.json
COPY src/index.html /app/index.html

EXPOSE 40819
CMD ["python", "app.py"]
