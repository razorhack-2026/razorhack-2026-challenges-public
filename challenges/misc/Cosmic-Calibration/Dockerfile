FROM python:3.12-slim
RUN useradd -m ctf && pip install --no-cache-dir "numpy>=1.21"
WORKDIR /app
COPY src/rubik2d.py .
COPY src/assets/cube_solved.png assets/
COPY src/web/server.py web/
COPY src/web/static/ web/static/
USER ctf
ENV PORT=8082
EXPOSE 8082
CMD ["python3", "web/server.py"]
