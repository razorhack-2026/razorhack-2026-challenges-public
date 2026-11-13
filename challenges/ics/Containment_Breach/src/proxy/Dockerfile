# Competitor-facing front for the Ignition gateway (see nginx.conf), with its config baked in.
# Build context: src/proxy   (docker compose build, or tools/challenge_images.py)
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY proxy_common.conf /etc/nginx/proxy_common.conf
EXPOSE 8088
