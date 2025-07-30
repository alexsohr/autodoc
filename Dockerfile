# syntax=docker/dockerfile:1-labs

FROM node:20-alpine AS node_base

FROM node_base AS node_deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

FROM node_base AS node_builder
WORKDIR /app
COPY --from=node_deps /app/node_modules ./node_modules
# Copy only necessary files for Next.js build
COPY package.json package-lock.json next.config.ts tsconfig.json tailwind.config.js postcss.config.mjs ./
COPY src/ ./src/
COPY public/ ./public/
# Increase Node.js memory limit for build and disable telemetry
ENV NODE_OPTIONS="--max-old-space-size=4096"
ENV NEXT_TELEMETRY_DISABLED=1
RUN NODE_ENV=production npm run build

FROM python:3.11-slim AS py_deps
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY api/requirements.txt ./api/
RUN pip install --no-cache -r api/requirements.txt

# Use Python 3.11 as final image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    git \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/venv/bin:$PATH"

# Copy Python dependencies
COPY --from=py_deps /opt/venv /opt/venv
COPY api/ ./api/

# Copy Node app
COPY --from=node_builder /app/public ./public
COPY --from=node_builder /app/.next/standalone ./
COPY --from=node_builder /app/.next/static ./.next/static

# Expose the port the app runs on
EXPOSE ${PORT:-8001} ${NEXT_PORT:-3000}

# Create a script to run both backend and frontend with proper process management
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to cleanup processes on exit\n\
cleanup() {\n\
    echo "Shutting down services..."\n\
    jobs -p | xargs -r kill\n\
    exit\n\
}\n\
\n\
# Set up signal handlers\n\
trap cleanup SIGTERM SIGINT\n\
\n\
# Load environment variables from .env file if it exists\n\
if [ -f .env ]; then\n\
  export $(grep -v "^#" .env | xargs -r)\n\
fi\n\
\n\
# Set default port values\n\
export API_PORT=${PORT:-8001}\n\
export NEXT_PORT=${NEXT_PORT:-3000}\n\
\n\
# Check for required environment variables\n\
if [ -z "$OPENAI_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then\n\
  echo "Warning: OPENAI_API_KEY and/or GOOGLE_API_KEY environment variables are not set."\n\
  echo "These are required for AutoDoc to function properly."\n\
  echo "You can provide them via a mounted .env file or as environment variables when running the container."\n\
fi\n\
\n\
echo "Starting API server on port $API_PORT..."\n\
python -m api.main --port $API_PORT &\n\
API_PID=$!\n\
\n\
# Wait a moment for API server to start\n\
sleep 2\n\
\n\
echo "Starting Next.js server on port $NEXT_PORT..."\n\
PORT=$NEXT_PORT HOSTNAME=0.0.0.0 node server.js &\n\
NEXT_PID=$!\n\
\n\
echo "Services started - API PID: $API_PID, Next.js PID: $NEXT_PID"\n\
echo "API available at: http://0.0.0.0:$API_PORT"\n\
echo "Frontend available at: http://0.0.0.0:$NEXT_PORT"\n\
\n\
# Wait for any process to exit\n\
wait -n\n\
\n\
# If we get here, one of the processes has exited\n\
echo "One of the services has stopped. Shutting down..."\n\
cleanup' > /app/start.sh && chmod +x /app/start.sh

# Set environment variables
ENV PORT=8001
ENV NEXT_PORT=3000
ENV NODE_ENV=production
ENV SERVER_BASE_URL=http://localhost:${PORT:-8001}

# Create empty .env file (will be overridden if one exists at runtime)
RUN touch .env

# Command to run the application
CMD ["/app/start.sh"]
