# =============================================================================
# Aegis Frontend - Development Dockerfile
# =============================================================================
# Uses Node to run Vite dev server with hot reload

FROM node:22-alpine

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Expose Vite dev server port
EXPOSE 3000

# Run Vite dev server
# --host exposes to Docker network
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

