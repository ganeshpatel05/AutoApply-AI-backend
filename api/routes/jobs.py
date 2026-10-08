from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from api.schemas.models import JobSearchRequest, CustomJdMatchRequest
from database.db_manager import DatabaseManager
from tools.ats_scorer import ATSScorer

router = APIRouter(prefix="/jobs", tags=["jobs"])
db = DatabaseManager()
ats = ATSScorer()

@router.get("/")
def get_jobs(search: Optional[str] = "", min_ats: float = 0):
    try:
        jobs = db.get_all_jobs(search=search, min_ats=min_ats)
        return {"success": True, "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}")
def get_job(job_id: int):
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"success": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search-new")
def search_new_jobs(req: JobSearchRequest):
    try:
        from agents.job_search_agent import JobSearchAgent
        agent = JobSearchAgent(db)
        jobs = agent.search_and_store(
            role=req.role,
            location=req.location,
            experience=req.experience,
            demo_mode=req.demo_mode
        )
        return {"success": True, "count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/match-custom")
def match_custom_jd(req: CustomJdMatchRequest):
    try:
        resume_text = ""
        if req.resume_text and req.resume_text.strip():
            resume_text = req.resume_text.strip()
        elif req.resume_id:
            res_data = db.get_resume_by_id(req.resume_id)
            if res_data:
                resume_text = res_data.get("raw_text", "")
        
        if not resume_text:
            active_resume = db.get_active_resume()
            if active_resume:
                resume_text = active_resume.get("raw_text", "")
                
        if not resume_text:
            raise HTTPException(status_code=404, detail="Please upload or paste a resume to calculate match.")

        from tools.ats_scorer import ATSScorer
        scorer = ATSScorer()
        res = scorer.score(resume_text, req.jd_text)

        match_result = {
            "ats_score": res["score"],
            "recommendation": res["recommendation"],
            "matched_keywords": res["matched_keywords"],
            "missing_keywords": res["missing_keywords"],
            "breakdown": res.get("breakdown", {}),
            "job_title": req.job_title,
            "company": req.company,
            "company_type": req.company_type or "MNC (Multi National Company)",
            "is_mnc": req.is_mnc if req.is_mnc is not None else True
        }
        return {"success": True, "match_result": match_result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/toggle-save")
def toggle_save_job(job_id: int):
    try:
        new_state = db.toggle_save_job(job_id)
        return {"success": True, "is_saved": new_state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{job_id}/match")
def match_job_to_resume(job_id: int):
    try:
        job = db.get_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
            
        resume = db.get_active_resume()
        if not resume:
            raise HTTPException(status_code=404, detail="No active resume to match against")
            
        # Need to format for ATSScorer which expects dicts with title/description
        job_for_ats = [{
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "jd_text": (job["description"] or "") + " " + (job["requirements"] or ""),
            "url": job["url"],
            "source": job["source"]
        }]
        
        scored = ats.rank_jobs(resume["raw_text"], job_for_ats)
        if scored:
            result = scored[0]
            db.update_job_ats(
                job_id=job_id,
                ats_score=result["ats_score"],
                matched=result.get("matched_keywords", []),
                missing=result.get("missing_keywords", [])
            )
            return {"success": True, "match_result": result}
            
        raise HTTPException(status_code=500, detail="Matching failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
