from fastapi import APIRouter, HTTPException
from api.schemas.models import ApplicationStatusUpdate, ApplicationCreate
from database.db_manager import DatabaseManager

router = APIRouter(prefix="/applications", tags=["applications"])
db = DatabaseManager()

@router.get("/")
def get_applications():
    try:
        apps = db.get_all_applications()
        return {"success": True, "applications": apps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def create_application(req: ApplicationCreate):
    try:
        app_id = db.create_application(
            job_id=req.job_id,
            status=req.status or "Saved",
            cover_letter=req.cover_letter or "",
            resume_used=req.resume_used or "",
            email=req.email or "",
            notes=req.notes or ""
        )
        app = db.get_application_by_id(app_id)
        return {"success": True, "application": app}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{app_id}")
def get_application(app_id: int):
    try:
        app = db.get_application_by_id(app_id)
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"success": True, "application": app}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{app_id}/status")
def update_status(app_id: int, status_update: ApplicationStatusUpdate):
    try:
        db.update_application_status(app_id, status_update.status, status_update.notes)
        return {"success": True, "message": "Status updated successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{app_id}")
def delete_application(app_id: int):
    try:
        db.delete_application(app_id)
        return {"success": True, "message": "Application deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
