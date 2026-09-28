FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /workspace

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy arena code
COPY . .

# Environment variables with sensible defaults
ENV ARENA_MODEL="tencent/Hy-MT2-7B"
ENV ARENA_QUANT="none"
ENV PORT=8000

EXPOSE 8000

CMD ["python", "server.py"]
