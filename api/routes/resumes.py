import asyncio
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from database.db_manager import DatabaseManager
from tools.resume_parser import ResumeParser
import os
import shutil

from api.schemas.models import ResumeGenerateRequest
from agents.resume_agent import ResumeAgent

router = APIRouter(prefix="/resumes", tags=["resumes"])
db = DatabaseManager()
parser = ResumeParser()
resume_agent = ResumeAgent(db)



def _process_resume_upload(content: bytes, filename: str) -> dict:
    """Process resume upload in a thread to avoid blocking the event loop."""
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Parse resume (CPU + I/O intensive)
    parsed_data = parser.parse_pdf(file_path)
    
    if not parsed_data or not parsed_data.get("raw_text"):
        raise HTTPException(status_code=422, detail="Could not extract text from the provided file.")

    # Save to database
    resume_id = db.save_resume(
        name=parsed_data.get("name", "Unknown"),
        email=parsed_data.get("email", ""),
        phone=parsed_data.get("phone", ""),
        file_path=file_path,
        raw_text=parsed_data.get("raw_text", ""),
        skills=parsed_data.get("skills", []),
        experience=parsed_data.get("experience", ""),
        education=parsed_data.get("education", ""),
        linkedin=parsed_data.get("linkedin", ""),
        github=parsed_data.get("github", "")
    )
    
    return {"success": True, "resume_id": resume_id, "data": parsed_data}


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        # Read file content asynchronously
        content = await file.read()
        
        # Offload blocking I/O to thread pool
        result = await asyncio.to_thread(_process_resume_upload, content, file.filename)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
def get_active_resume():
    try:
        resume = db.get_active_resume()
        if not resume:
            return {"success": False, "resume": None, "message": "No active resume found."}
        return {"success": True, "resume": resume}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active/score")
def get_active_resume_score():
    try:
        resume = db.get_active_resume()
        if not resume:
            return {"success": False, "score": None, "message": "No active resume found."}
        
        from agents.resume_agent import ResumeAgent
        resume_agent = ResumeAgent(db)
        score_details = resume_agent.score_resume(resume)
        return {"success": True, "score": score_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_all_resumes():
    try:
        resumes = db.get_all_resumes()
        return {"success": True, "resumes": resumes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
def generate_resume(req: ResumeGenerateRequest):
    try:
        result = resume_agent.generate_resume_from_details(req.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

