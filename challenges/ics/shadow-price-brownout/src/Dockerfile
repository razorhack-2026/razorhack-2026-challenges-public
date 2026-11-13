# Shadow Price — PMC-7 OPC UA server.
# Stage 1 runs the design checks as a build gate, then bakes the model with scipy.
# Stage 2 is the runtime: asyncua only, no solver, no model source.

FROM python:3.12-slim AS bake
WORKDIR /build
RUN pip install --no-cache-dir numpy==2.5.3 scipy==1.18.1
COPY model.py shadow_price_lp.py bake.py ./
RUN python shadow_price_lp.py > /dev/null && python bake.py /build/baked.json

FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir asyncua==2.0.1
COPY server.py ./
COPY --from=bake /build/baked.json ./
USER nobody
EXPOSE 4840
CMD ["python", "-u", "server.py"]
