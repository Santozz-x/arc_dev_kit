# Arc DevKit — Mainnet Demo API (arc_devkit.api.demo_app)
#
# Builds and runs ONLY the read-only demo backend documented in
# demo/README.md. It never needs ANTHROPIC_API_KEY or ARC_PRIVATE_KEY —
# arc_devkit.config is never imported by this service.
#
# Build (from the repository root):
#   docker build -f demo/Dockerfile -t arc-devkit-demo-api .
#
# Run:
#   docker run -p 8010:8010 \
#     -e DEMO_ALLOWED_ORIGINS=https://your-docs-site.example.com \
#     arc-devkit-demo-api

FROM python:3.11-slim

WORKDIR /app

# Install the package itself (editable install of this checkout — the demo
# API depends on arc_devkit.demo_app, which is not yet published to PyPI).
COPY pyproject.toml ./
COPY arc_devkit ./arc_devkit
RUN pip install --no-cache-dir .

# uvicorn is a transitive dependency of the `api` extras already declared
# in pyproject.toml's core dependencies (fastapi/uvicorn) — no extra install.

EXPOSE 8010

# No ANTHROPIC_API_KEY, no ARC_PRIVATE_KEY — see arc_devkit/api/demo_app.py
# module docstring for the full list of (optional) env vars this service reads.
CMD ["uvicorn", "arc_devkit.api.demo_app:app", "--host", "0.0.0.0", "--port", "8010"]
