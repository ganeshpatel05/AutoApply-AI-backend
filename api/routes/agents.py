from fastapi import APIRouter, HTTPException, BackgroundTasks
from database.db_manager import DatabaseManager
from agents.orchestrator import AutoApplyOrchestrator
from api.schemas.models import PipelineRequest

router = APIRouter(prefix="/agents", tags=["agents"])
db = DatabaseManager()

@router.get("/logs")
def get_agent_logs():
    try:
        logs = db.get_agent_logs(limit=50)
        return {"success": True, "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/run-pipeline")
def run_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    orchestrator = AutoApplyOrchestrator(db)
    
    # Run in background to avoid blocking the UI
    background_tasks.add_task(
        orchestrator.run_pipeline,
        role=req.role,
        location=req.location,
        experience=req.experience,
        demo_mode=req.demo_mode,
        generate_cover_letters_count=req.generate_cover_letters_count
    )
    
    return {"success": True, "message": "Pipeline started in the background."}
