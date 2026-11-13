FROM python:3.12-slim
WORKDIR /app
# Built from src/ (docker-compose.yml and Razorhack-Infra alike) so the Sherlock site
# template from src/recon/ is baked in: a Fargate copy has no bind mounts.
COPY webmail/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY webmail/config.py webmail/rubric.py webmail/app.py ./
COPY webmail/templates ./templates
COPY recon/sherlock-sites.template.json ./
ENV SHERLOCK_TEMPLATE=/app/sherlock-sites.template.json
EXPOSE 8080
# Single process: the in-memory per-token state (cooldown, budget, thread history)
# must stay in one worker's memory. See app.py's module docstring.
CMD ["python", "-u", "app.py"]
