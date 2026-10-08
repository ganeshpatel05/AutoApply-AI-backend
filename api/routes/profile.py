from fastapi import APIRouter, HTTPException
from database.db_manager import DatabaseManager
from api.schemas.models import ProfileCreate, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])
db = DatabaseManager()

@router.get("/")
def get_profile():
    """Fetch candidate profile data."""
    try:
        profile = db.get_profile()
        if not profile:
            # Fallback to creating a profile from active resume if exists
            active_resume = db.get_active_resume()
            if active_resume:
                db.save_profile(
                    full_name=active_resume.get("name", "Candidate"),
                    email=active_resume.get("email", ""),
                    phone=active_resume.get("phone", ""),
                    experience=active_resume.get("experience", ""),
                    education=active_resume.get("education", ""),
                    linkedin=active_resume.get("linkedin", ""),
                    github=active_resume.get("github", ""),
                    skills=active_resume.get("skills", [])
                )
                profile = db.get_profile()

        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
@router.put("/")
def save_profile(req: ProfileCreate):
    """Save or update candidate profile."""
    try:
        pid = db.save_profile(
            full_name=req.full_name,
            email=req.email,
            phone=req.phone,
            location=req.location,
            target_roles=req.target_roles,
            experience=req.experience,
            education=req.education,
            linkedin=req.linkedin,
            github=req.github,
            skills=req.skills,
            theme_pref=req.theme_pref
        )
        updated = db.get_profile()
        return {"success": True, "profile": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
