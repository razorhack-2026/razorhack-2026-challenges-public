# The model server for a Fargate copy (Razorhack-Infra lib/challenges.json): Ollama on
# CPU with OLLAMA_MODEL already pulled, so a team's copy starts without downloading it.
# Only the CPU runtime is kept; the stock image's CUDA and MLX libraries (~4.5 GB) are
# left behind. docker-compose.yml's own `ollama` service (stock image, pull by hand)
# is unchanged for local runs.
FROM ollama/ollama:0.40.14 AS pull
ARG OLLAMA_MODEL=qwen2.5:3b-instruct
ENV OLLAMA_MODELS=/models
RUN set -e; ollama serve >/tmp/serve.log 2>&1 & pid=$!; \
    for i in $(seq 1 30); do ollama list >/dev/null 2>&1 && break; sleep 1; done; \
    ollama pull "$OLLAMA_MODEL"; ollama show "$OLLAMA_MODEL" >/dev/null; kill $pid; \
    rm -rf /usr/lib/ollama/cuda_* /usr/lib/ollama/mlx_* /usr/lib/ollama/rocm* /usr/lib/ollama/vulkan /usr/lib/ollama/include

FROM ubuntu:24.04
COPY --from=pull /usr/bin/ollama /usr/bin/ollama
COPY --from=pull /usr/lib/ollama /usr/lib/ollama
COPY --from=pull /models /models
# Loopback only: in a Fargate copy every listening port is reachable from the team's
# Kali box, and only persona should talk to the model. Keep it loaded between replies.
ENV OLLAMA_MODELS=/models OLLAMA_HOST=127.0.0.1:11434 OLLAMA_KEEP_ALIVE=-1
ENTRYPOINT ["/usr/bin/ollama"]
CMD ["serve"]
