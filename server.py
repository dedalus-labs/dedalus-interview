"""Inventory API — uv run uvicorn server:app --port 8000"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client

load_dotenv()

app = FastAPI()

db = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/check")
async def check_availability(payload: dict):
    result = (
        db.table("inventory")
        .select("*")
        .eq("sku", payload["sku"])
        .execute()
    )
    if not result.data:
        return {"available": False, "items": []}
    row = result.data[0]
    return {
        "available": row["quantity"] >= payload.get("quantity", 1),
        "items": result.data,
    }
