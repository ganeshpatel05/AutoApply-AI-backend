from fastapi import APIRouter, HTTPException
from database.db_manager import DatabaseManager
from tools.ollama_client import OllamaClient
from tools.email_sender import EmailSender
from api.schemas.models import OllamaModelSwitchRequest
from config.settings import EMAIL_SENDER, OLLAMA_BASE_URL

router = APIRouter(prefix="/system", tags=["system"])
db = DatabaseManager()
ollama = OllamaClient()

@router.get("/status")
def get_system_status(force: bool = False):
    """Detailed health & status check of all core application subsystems."""
    try:
        # Check Database
        db_status = "healthy"
        stats = db.get_stats()
        
        # Check Ollama
        ollama_online = ollama.is_available(force=force)
        installed_models = ollama.list_models() if ollama_online else []
        active_model = ollama.get_active_model() if ollama_online else ""
        
        # Email config status
        email_configured = bool(EMAIL_SENDER)

        return {
            "success": True,
            "system": {
                "api": "healthy",
                "database": {
                    "status": db_status,
                    "total_jobs": stats.get("total_jobs", 0),
                    "total_apps": stats.get("total_apps", 0)
                },
                "ollama": {
                    "status": "connected" if ollama_online else "offline",
                    "base_url": ollama.base_url,
                    "active_model": active_model,
                    "installed_models": installed_models
                },
                "email": {
                    "configured": email_configured,
                    "sender": EMAIL_SENDER if email_configured else None
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ollama")
def get_ollama_status():
    """Get live status of local Ollama AI engine."""
    online = ollama.is_available()
    models = ollama.list_models() if online else []
    active = ollama.get_active_model() if online else ""
    return {
        "success": True,
        "online": online,
        "base_url": ollama.base_url,
        "active_model": active,
        "installed_models": models
    }

@router.post("/ollama/switch")
def switch_ollama_model(req: OllamaModelSwitchRequest):
    """Switch active Ollama model in runtime client."""
    ollama.configured_model = req.model
    ollama._cached_model = req.model
    return {
        "success": True,
        "active_model": req.model,
        "message": f"Active Ollama model switched to '{req.model}'"
    }
