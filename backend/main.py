"""
main.py
--------
FastAPI application entry point for the n8n Agentic Workflow Builder.

Run with:
  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
import logging

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="n8n Agentic Workflow Builder",
    description=(
        "An agentic AI system that converts natural language automation requests "
        "into executable n8n workflows using LangGraph, Gemini 2.5 Flash, "
        "and a dynamic n8n node registry."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(router, prefix="/api/v1")


# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "n8n Agentic Workflow Builder",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "chat": "/api/v1/chat",
    }


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
