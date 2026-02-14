# Gonka.ai K2.5 Model Serving Container
#
# Serves Kimi K2.5 via vLLM with OpenAI-compatible API.
# Requires NVIDIA GPU runtime (--gpus all).
#
# Build:
#   docker build -t gonka-k25-serving -f infrastructure/serving/Dockerfile .
#
# Run (full precision, 8 GPUs):
#   docker run --gpus all -p 8000:8000 gonka-k25-serving
#
# Run (custom config):
#   docker run --gpus all -p 8000:8000 \
#     -e GONKA_TP_SIZE=4 \
#     -e GONKA_MAX_MODEL_LEN=65536 \
#     gonka-k25-serving

FROM vllm/vllm-openai:latest

LABEL maintainer="Gonka.ai"
LABEL description="Kimi K2.5 inference via vLLM"

# Install additional dependencies
RUN pip install --no-cache-dir httpx

# Copy serving code
COPY infrastructure/serving/ /app/serving/
COPY infrastructure/config/ /app/config/

WORKDIR /app

# Environment defaults
ENV GONKA_MODEL="moonshotai/Kimi-K2.5"
ENV GONKA_TP_SIZE="8"
ENV GONKA_MAX_MODEL_LEN="131072"
ENV GONKA_GPU_MEM_UTIL="0.92"
ENV GONKA_HOST="0.0.0.0"
ENV GONKA_PORT="8000"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:${GONKA_PORT}/health'); exit(0 if r.status_code == 200 else 1)" \
    || exit 1

EXPOSE ${GONKA_PORT}

# Launch vLLM with Gonka defaults
ENTRYPOINT ["python", "-m", "vllm.entrypoints.openai.api_server"]
CMD ["--model", "moonshotai/Kimi-K2.5", \
     "--tensor-parallel-size", "8", \
     "--max-model-len", "131072", \
     "--gpu-memory-utilization", "0.92", \
     "--tool-call-parser", "kimi_k2", \
     "--reasoning-parser", "kimi_k2", \
     "--mm-encoder-tp-mode", "data", \
     "--trust-remote-code", \
     "--host", "0.0.0.0", \
     "--port", "8000"]
