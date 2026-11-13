FROM python:3.12-slim
RUN useradd -m ctf
WORKDIR /app
COPY src/server.py .
USER ctf
ENV PORT=8000
EXPOSE 8000
CMD ["python3", "server.py"]
