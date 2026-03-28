# Inventory service

**Objective:** With local Supabase running and the API server up, `uv run python harness.py` must exit successfully.

---

**1. Environment** — Docker (for Supabase) and a way to run the Supabase CLI (`npx supabase` is enough). On **GitHub Codespaces**, open the repo with the **devcontainer** so Docker-in-Docker is available; `scripts/post-create.sh` installs `uv` and runs `uv sync`. On a **Mac**, install Docker Desktop yourself; no script can do that for you.

**2. Server** — Optimize `server.py` so the harness passes. Run the app with `uv sync` and `uv run uvicorn server:app --port 8000`, then `uv run python harness.py` to verify.
