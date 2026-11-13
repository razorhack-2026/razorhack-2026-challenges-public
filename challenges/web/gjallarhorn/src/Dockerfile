FROM node:22-alpine AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# validator only: public key + verify code. The private key and generator never enter the image.
COPY launch_token.py ./
COPY keys/token_pub.pem ./keys/token_pub.pem
COPY server/app.py server/secret.json ./server/
COPY --from=ui /ui/dist ./server/static
ENV KEYS_DIR=/app STATIC_DIR=/app/server/static
RUN useradd -r -u 10001 app
USER app
EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "--threads", "8", "--chdir", "/app/server", "app:app"]
