FROM python:3.12-slim

RUN useradd -m ctf
WORKDIR /home/ctf
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py flag.txt ./
COPY static ./static
RUN chown root:ctf flag.txt && chmod 440 flag.txt

USER ctf
ENV PYTHONUNBUFFERED=1
EXPOSE 5000
# One worker on purpose: game state lives in this process's memory.
# Threads give concurrency; a per-session lock keeps each run consistent.
CMD ["gunicorn", "-w", "1", "--threads", "32", "-b", "0.0.0.0:5000", "app:app"]
