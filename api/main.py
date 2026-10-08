import os
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes import agents, resumes, jobs, applications, cover_letters, analytics, system, profile

app = FastAPI(
    title="AutoApply AI / CareerPilot AI API",
    description="Backend API for AutoApply AI multi-agent platform",
    version="1.0.0"
)

# Dynamic CORS Configuration for Production / Live Hosting
raw_allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
if raw_allowed_origins:
    origins = [origin.strip() for origin in raw_allowed_origins.split(",") if origin.strip()]
else:
    # Default development and production wildcard fallback
    origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app" if not raw_allowed_origins else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    from database.db_manager import DatabaseManager
    from config.settings import RESUME_UPLOAD_DIR, CL_UPLOAD_DIR
    # Ensure directories exist
    try:
        RESUME_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        CL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    # Ensure database tables exist
    db = DatabaseManager()
    db.init_db()

routers = [
    analytics.router,
    agents.router,
    resumes.router,
    jobs.router,
    applications.router,
    cover_letters.router,
    system.router,
    profile.router,
]

for r in routers:
    app.include_router(r)                  # Handles /resumes/active when Vercel strips /api/
    app.include_router(r, prefix="/api")   # Handles /api/resumes/active when request retains /api/

@app.get("/")
@app.get("/api")
def read_root():
    return {"message": "Welcome to AutoApply AI API"}

@app.get("/health")
@app.get("/api/health")
def health_check():
    from database.db_manager import DatabaseManager
    from tools.ollama_client import OllamaClient
    
    db = DatabaseManager()
    ollama = OllamaClient()
    ollama_online = ollama.is_available()
    
    return {
        "status": "healthy",
        "service": "autoapply-ai-api",
        "database": "healthy",
        "ollama": "connected" if ollama_online else "offline",
        "model": ollama.get_active_model() if ollama_online else None
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    import asyncio
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)

