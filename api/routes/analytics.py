from fastapi import APIRouter, HTTPException
from database.db_manager import DatabaseManager

router = APIRouter(prefix="/analytics", tags=["analytics"])
db = DatabaseManager()

@router.get("/")
def get_dashboard_stats():
    try:
        stats = db.get_stats()
        camel_case_stats = {
            "totalJobs": stats.get("total_jobs", 0),
            "savedJobs": stats.get("saved_jobs", 0),
            "applications": stats.get("total_apps", 0),
            "savedApps": stats.get("saved_apps", 0),
            "appliedApps": stats.get("applied_apps", 0),
            "screeningApps": stats.get("screening_apps", 0),
            "emailsSent": stats.get("emails_sent", 0),
            "interviews": stats.get("interviews", 0),
            "offers": stats.get("offers", 0),
            "rejected": stats.get("rejected", 0),
            "withdrawn": stats.get("withdrawn", 0),
            "averageAtsScore": stats.get("avg_ats", 0.0)
        }
        return {"success": True, "stats": camel_case_stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ats-breakdown")
def get_ats_breakdown():
    try:
        data = db.get_ats_details()
        return {"success": True, "ats": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversion-details")
def get_conversion_details():
    try:
        data = db.get_conversion_details()
        return {"success": True, "conversion": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

