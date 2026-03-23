# ── Stage: base image ────────────────────────────────────────────────────────
# FROM tells Docker which base image to start from.
# python:3.13-slim is an official image — a minimal Linux (Debian) with
# Python 3.13 already installed. "slim" means no extras, keeps it small.
FROM python:3.13-slim

# ── Working directory ─────────────────────────────────────────────────────────
# WORKDIR sets the folder we work inside the container.
# All following commands run from here. Created automatically if missing.
WORKDIR /app

# ── Create a virtual environment ──────────────────────────────────────────────
# This is the venv we skipped earlier — inside Docker we always use one.
# It lives at /venv inside the container, completely isolated.
RUN python -m venv /venv

# ── Put the venv on PATH ──────────────────────────────────────────────────────
# ENV sets an environment variable that persists for all future RUN/CMD steps.
# This is equivalent to "source /venv/bin/activate" — all pip/python commands
# now use the venv automatically.
ENV PATH="/venv/bin:$PATH"

# ── Install dependencies ──────────────────────────────────────────────────────
# COPY src dest — copies files from your machine into the container.
# We copy requirements.txt first (before the rest of the code) so Docker can
# cache this layer. If requirements.txt hasn't changed, Docker skips this step
# on the next build — saves a lot of time.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy the rest of the backend code ────────────────────────────────────────
# Now copy everything else. This layer re-runs on every code change,
# but the pip install layer above is still cached.
COPY . .

# ── Expose port ───────────────────────────────────────────────────────────────
# EXPOSE documents which port this container listens on.
# It doesn't actually open the port — docker-compose does that.
# Create the data directory for the SQLite database
RUN mkdir -p /app/data

EXPOSE 8000

# ── Start command ─────────────────────────────────────────────────────────────
# CMD is the command that runs when the container starts.
# --host 0.0.0.0 means "listen on all network interfaces inside the container"
# Without this, uvicorn binds to 127.0.0.1 which is unreachable from outside
# the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
