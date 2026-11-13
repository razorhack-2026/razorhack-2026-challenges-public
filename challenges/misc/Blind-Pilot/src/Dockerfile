FROM python:3.12-slim

RUN useradd -m ctf
WORKDIR /home/ctf
COPY server.py flag.txt ./
RUN chown root:ctf flag.txt && chmod 440 flag.txt

USER ctf
ENV PYTHONUNBUFFERED=1
EXPOSE 1337
CMD ["python3", "server.py", "--listen", "1337"]
