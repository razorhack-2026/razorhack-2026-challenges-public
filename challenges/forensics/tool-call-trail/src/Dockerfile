# Single image for the whole mesh + driver; ROLE / command selects the process.
FROM python:3.12-alpine
WORKDIR /app
COPY mesh.py /app/mesh.py
COPY driver.py /app/driver.py
ENV PORT=80
EXPOSE 80
CMD ["python", "-u", "mesh.py"]
