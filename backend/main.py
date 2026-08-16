"""
main.py — FastAPI application entry point.
Starts the server with Uvicorn on port 8004.
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import PORT, ENV, logger, BASE_DIR
from routers.analyze   import router as analyze_router
from routers.segment   import router as segment_router
from routers.composite import router as composite_router

# ─────────────────────────────────────────────
#  App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="E2M — Exterior to Material API",
    description="AI-based exterior house renovation and cost estimation system.",
    version="1.0.0",
)

# CORS — allow all origins for prototype
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  Static Files — texture swatches
# ─────────────────────────────────────────────

TEXTURES_DIR = os.path.join(BASE_DIR, "static", "textures")
os.makedirs(TEXTURES_DIR, exist_ok=True)
app.mount("/static/textures", StaticFiles(directory=TEXTURES_DIR), name="textures")

# ─────────────────────────────────────────────
#  Routers
# ─────────────────────────────────────────────

app.include_router(analyze_router)
app.include_router(segment_router)
app.include_router(composite_router)

from routers.visualize import router as visualize_router
app.include_router(visualize_router)


from routers.estimate import router as estimate_router
app.include_router(estimate_router)

from routers.report import router as report_router
app.include_router(report_router)



# ─────────────────────────────────────────────
#  Health Check
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "E2M API", "env": ENV}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ─────────────────────────────────────────────
#  Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    logger.info(f"Starting E2M backend on port {PORT} [{ENV}]")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=(ENV == "development"),
        log_level="info",
    )
