import asyncio
from fastapi import APIRouter, HTTPException
from api.schemas.models import CoverLetterGenerateRequest, CoverLetterUpdateRequest
from database.db_manager import DatabaseManager
from agents.cover_letter_agent import CoverLetterAgent
from tools.ats_scorer import ATSScorer
from tools.resume_parser import ResumeParser

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])
db = DatabaseManager()
cl_agent = CoverLetterAgent(db)
ats_scorer = ATSScorer()
resume_parser = ResumeParser()

@router.post("/generate")
async def generate_cover_letter(req: CoverLetterGenerateRequest):
    try:
        resume = db.get_active_resume()
        if not resume:
            raise HTTPException(status_code=400, detail="Please upload a resume before generating a personalized cover letter.")
        
        job = None
        if req.job_id:
            job = db.get_job_by_id(req.job_id)
        
        if not job and (req.custom_jd or req.job_title):
            job = {
                "id": req.job_id,
                "title": req.job_title or "Software Developer",
                "company": req.company_name or "Target Company",
                "description": req.custom_jd or f"Job position for {req.job_title or 'Software Developer'} at {req.company_name or 'Target Company'}.",
                "matched_keywords": []
            }
        
        if not job:
            raise HTTPException(status_code=400, detail="Please select a job before generating a cover letter.")

        tone = req.tone or "Professional"
        length = req.length or "Standard"
        variation = req.variation or 1
        
        # Offload LLM generation (10-60s blocking) to thread pool
        result = await asyncio.to_thread(
            cl_agent.generate_cover_letter,
            resume_data=resume,
            job=job,
            tone=tone,
            length=length,
            variation=variation
        )
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[api/cover-letters/generate] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{job_id}")
def get_cover_letter(job_id: int):
    try:
        cl = db.get_cover_letter(job_id)
        job = db.get_job_by_id(job_id)
        resume = db.get_active_resume()
        
        match_summary = None
        candidate_info = None
        job_info = None

        if resume and job:
            match_summary = ats_scorer.analyze_match(resume, job)
            profile = resume_parser.get_structured_profile(resume)
            candidate_info = {
                "name": profile.get("name", "Candidate"),
                "skills_count": len(profile.get("skills", [])),
                "resume_analyzed": True
            }
            job_info = {
                "id": job.get("id"),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", "")
            }

        return {
            "success": True,
            "cover_letter": cl,
            "match_summary": match_summary,
            "candidate_info": candidate_info,
            "job_info": job_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{job_id}")
def update_cover_letter(job_id: int, req: CoverLetterUpdateRequest):
    try:
        db.save_cover_letter(job_id=job_id, content=req.content)
        return {"success": True, "message": "Cover letter updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
