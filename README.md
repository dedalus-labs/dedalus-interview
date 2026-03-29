# Inventory service

*The following is a fictional narrative about some very real problems.*

## Context

Your API server has been running fine all morning. Health checks are green. No
deploys have gone out. No code has changed.

Then traffic spikes.

Suddenly, the server starts failing the harness. `GET /health` gets slow.
Requests pile up. The process is still alive, but under load it stops behaving
like a healthy service.

Your job is to figure out why this only breaks at higher traffic, and fix it.

## Objective

Make `uv run python harness.py` exit successfully.

## Stage 1: environment

Get the local database running for this repo.

- Make Docker available in the environment.
- Make the Supabase CLI available in the environment.
- Start the local Supabase stack for this repository.
- Create `.env` from `.env.example`.
- Fill in `SUPABASE_URL` and `SUPABASE_KEY` with working local values.
- Install the project dependencies.

## Stage 2: server

Run the API server and the harness for this repository.

Your task is to change `server.py` until the harness exits successfully.
