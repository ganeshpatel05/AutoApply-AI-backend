from pydantic import BaseModel, Field
from typing import List, Optional

class ProfileCreate(BaseModel):
    full_name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    target_roles: Optional[str] = ""
    experience: Optional[str] = ""
    education: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    skills: Optional[List[str]] = []
    theme_pref: Optional[str] = "light"

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    target_roles: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    skills: Optional[List[str]] = None
    theme_pref: Optional[str] = None

class PipelineRequest(BaseModel):
    role: str = "Software Developer"
    location: Optional[str] = ""
    experience: Optional[str] = "0"
    demo_mode: Optional[bool] = False
    generate_cover_letters_count: Optional[int] = 3

class ApplicationCreate(BaseModel):
    job_id: int
    status: Optional[str] = "Saved"
    cover_letter: Optional[str] = ""
    resume_used: Optional[str] = ""
    email: Optional[str] = ""
    notes: Optional[str] = ""

class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class JobSaveRequest(BaseModel):
    job_id: int

class JobSearchRequest(BaseModel):
    role: str = "Software Engineer"
    location: Optional[str] = ""
    experience: Optional[str] = "0"
    demo_mode: Optional[bool] = True

class CustomJdMatchRequest(BaseModel):
    jd_text: str
    job_title: Optional[str] = "Target Role"
    company: Optional[str] = "Target Company"
    company_type: Optional[str] = "MNC (Multi National Company)"
    is_mnc: Optional[bool] = True
    resume_text: Optional[str] = None
    resume_id: Optional[int] = None

class CoverLetterGenerateRequest(BaseModel):
    job_id: Optional[int] = None
    custom_jd: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    tone: Optional[str] = "Professional"
    length: Optional[str] = "Standard"
    variation: Optional[int] = 1
    custom_prompt: Optional[str] = None

class CoverLetterUpdateRequest(BaseModel):
    content: str

class OllamaModelSwitchRequest(BaseModel):
    model: str

class ResumeGenerateRequest(BaseModel):
    name: str
    email: Optional[str] = ""
    phone: Optional[str] = ""
    location: Optional[str] = ""
    linkedin: Optional[str] = ""
    github: Optional[str] = ""
    summary: Optional[str] = ""
    skills: Optional[List[str]] = []
    experience: Optional[str] = ""
    projects: Optional[str] = ""
    education: Optional[str] = ""
    enhance_with_ai: Optional[bool] = True

