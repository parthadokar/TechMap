# ── Base image ────────────────────────────────────────────────────────────────
# node:22-slim gives us Node 22 on minimal Linux.
# No more hunting for /run/host/usr/bin/node — it's just "node" inside here.
FROM node:22-slim

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install dependencies ──────────────────────────────────────────────────────
# Copy package files first (same caching trick as the backend).
# If package.json hasn't changed, Docker reuses the node_modules layer.
COPY package.json package-lock.json ./
RUN npm install

# ── Copy the rest of the frontend code ───────────────────────────────────────
COPY . .

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 5173

# ── Start command ─────────────────────────────────────────────────────────────
# --host exposes Vite outside the container (same reason as uvicorn's 0.0.0.0).
# Without --host, Vite only listens on 127.0.0.1 inside the container and
# you'd never be able to open it in your browser.
CMD ["npx", "vite", "dev", "--host"]
