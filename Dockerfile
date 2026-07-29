# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies (needed for compiling some Python packages)
RUN apt-get update && apt-get install -y gcc build-essential && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependencies first to maximize Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Runner (Lightweight Production Image)
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Copy ONLY the pre-compiled virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the actual application code
COPY ./app ./app

# We leave the CMD blank here and define it dynamically in docker-compose