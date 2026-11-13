FROM python:3.12-slim AS pdf-builder

# Where the website is actually reachable from a participant — baked into
# the manual's "for support, visit ..." line. Defaults to localhost:8080
# for local GM testing; override with --build-arg VENDOR_URL=... (or via
# docker-compose's build.args) at the real venue. Must match the drone's
# runtime VENDOR_URL env var (see ../drone and docker-compose.yml) so the
# FC43 response and the manual agree.
ARG VENDOR_URL=http://localhost:8080
ENV VENDOR_URL=${VENDOR_URL}

WORKDIR /build
RUN pip install --no-cache-dir reportlab==4.2.5
COPY generate_pdf.py .
COPY html/ ./html/

RUN mkdir -p /output && python generate_pdf.py

# ── nginx stage ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY html/ /usr/share/nginx/html/

RUN mkdir -p /usr/share/nginx/html/manuals
COPY --from=pdf-builder /output/DM-7_Operations_Manual_v2.3.pdf \
     /usr/share/nginx/html/manuals/DM-7_Operations_Manual_v2.3.pdf

EXPOSE 80
