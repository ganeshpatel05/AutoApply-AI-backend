"""AutoApply AI — Agent 1: Resume Agent
Extracts and structures resume information from PDF or plain text.
"""

from tools.resume_parser import ResumeParser
from tools.ollama_client import OllamaClient
from database.db_manager import DatabaseManager


class ResumeAgent:
    """Agent responsible for parsing resumes, scoring content, and providing AI analysis."""

    def __init__(self, db: DatabaseManager = None):
        self.parser = ResumeParser()
        self.ollama = OllamaClient()
        self.db = db or DatabaseManager()

    def process_pdf(self, pdf_path: str) -> dict:
        """Parse PDF resume, save to database, mark active and return data."""
        data = self.parser.parse_pdf(pdf_path)
        filename = pdf_path.replace("\\", "/").split("/")[-1]
        
        resume_id = self.db.save_resume(
            name=data.get("name", "Candidate"),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            file_path=pdf_path,
            raw_text=data.get("raw_text", ""),
            skills=data.get("skills", []),
            experience=data.get("experience", ""),
            education=data.get("education", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", "")
        )
        data["db_id"] = resume_id
        self.db.log_agent_activity("ResumeMind", f"Parsed PDF resume '{data.get('name')}'", "Completed", f"Extracted {len(data.get('skills', []))} skills")
        return data

    def process_text(self, name: str, text: str) -> dict:
        """Parse plain text resume, save to database and return data."""
        data = self.parser.parse_text(text)
        data["name"] = name or data.get("name", "Candidate")
        
        resume_id = self.db.save_resume(
            name=data["name"],
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            file_path="",
            raw_text=data.get("raw_text", ""),
            skills=data.get("skills", []),
            experience=data.get("experience", ""),
            education=data.get("education", ""),
            linkedin=data.get("linkedin", ""),
            github=data.get("github", "")
        )
        data["db_id"] = resume_id
        self.db.log_agent_activity("ResumeMind", f"Parsed text resume '{data['name']}'", "Completed", f"Extracted {len(data.get('skills', []))} skills")
        return data

    def get_active_resume(self) -> dict | None:
        """Fetch current active resume from SQLite database."""
        return self.db.get_active_resume()

    def score_resume(self, data: dict) -> dict:
        """Calculate a detailed resume quality score and generate AI-driven feedback."""
        content_score = 0
        skills_score = 0
        experience_score = 0
        education_score = 0
        completeness_score = 0

        raw_text = data.get("raw_text", "")
        wc = data.get("word_count", len(raw_text.split()) if raw_text else 0)

        # Content (Word Count & Depth)
        if wc > 500: content_score = 95
        elif wc > 250: content_score = 80
        elif wc > 100: content_score = 50
        else: content_score = 25

        # Skills
        skills = data.get("skills", [])
        if len(skills) > 15: skills_score = 95
        elif len(skills) > 8: skills_score = 80
        elif len(skills) > 3: skills_score = 50
        else: skills_score = 20

        # Experience
        exp = data.get("experience", "")
        if len(exp) > 300: experience_score = 95
        elif len(exp) > 100: experience_score = 70
        elif len(exp) > 20: experience_score = 40
        else: experience_score = 20

        # Education
        edu = data.get("education", "")
        if len(edu) > 50: education_score = 95
        elif len(edu) > 10: education_score = 65
        else: education_score = 30

        # Completeness (Contact Info)
        fields = ["email", "phone", "linkedin", "github"]
        found_fields = sum(1 for f in fields if data.get(f))
        completeness_score = min(100, found_fields * 25)

        # Weighted Total
        total = int((content_score * 0.15) + (skills_score * 0.3) + (experience_score * 0.3) + (education_score * 0.15) + (completeness_score * 0.1))

        # Actionable Suggestions (AI-powered with fallback)
        suggestions = []
        if self.ollama.is_available() and raw_text:
            ai_res = self.ollama.generate(
                prompt=f"""Analyze the following resume content and list 3 concise, highly actionable bullet points to improve its ATS match rate, impact metrics, and technical presentation.

Resume Content:
{raw_text[:2500]}

Format strictly as bullet points starting with '- '. Keep each suggestion under 20 words.""",
                system_prompt="You are an expert ATS resume consultant."
            )
            if ai_res["success"] and ai_res["text"]:
                lines = [l.strip("-•* ").strip() for l in ai_res["text"].split("\n") if l.strip()]
                suggestions = [l for l in lines if len(l) > 10][:4]

        # Rule-based fallback suggestions if AI returned no results or is unavailable
        if not suggestions:
            if len(skills) < 10:
                suggestions.append("Add more specific technical frameworks & tools to your Skills section.")
            if "metrics" not in raw_text.lower() and "%" not in raw_text:
                suggestions.append("Include measurable impact and metrics (e.g. 'Improved efficiency by 30%') in project descriptions.")
            if not data.get("linkedin"):
                suggestions.append("Add a valid LinkedIn profile URL to boost profile credibility.")
            if not data.get("github"):
                suggestions.append("Add a GitHub profile link to demonstrate code repositories.")
            if len(exp) < 150:
                suggestions.append("Expand work experience and key technical project details.")

        if not suggestions:
            suggestions.append("Great resume profile! Keep your project achievements updated with recent tech stacks.")

        return {
            "content": content_score,
            "skills": skills_score,
            "experience": experience_score,
            "education": education_score,
            "completeness": completeness_score,
            "suggestions": suggestions,
            "total": total
        }

    def generate_resume_from_details(self, details: dict) -> dict:
        """Generate an ATS-optimized resume from user-provided details and save as active resume."""
        name = details.get("name") or "Candidate"
        email = details.get("email") or ""
        phone = details.get("phone") or ""
        location = details.get("location") or ""
        linkedin = details.get("linkedin") or ""
        github = details.get("github") or ""
        summary = details.get("summary") or ""
        skills = details.get("skills") if isinstance(details.get("skills"), list) else []
        if isinstance(details.get("skills"), str):
            skills = [s.strip() for s in details.get("skills").split(",") if s.strip()]
        
        experience = details.get("experience") or ""
        projects = details.get("projects") or ""
        education = details.get("education") or ""
        enhance = details.get("enhance_with_ai", True)

        # Build clean raw text sections
        header_lines = [name.upper()]
        contact_parts = [p for p in [email, phone, location, linkedin, github] if p]
        if contact_parts:
            header_lines.append(" | ".join(contact_parts))
        
        sections = ["\n".join(header_lines)]

        if summary:
            sections.append(f"\nPROFESSIONAL SUMMARY\n{summary}")

        if skills:
            sections.append(f"\nTECHNICAL SKILLS\n" + ", ".join(skills))

        if experience:
            sections.append(f"\nPROFESSIONAL EXPERIENCE\n{experience}")

        if projects:
            sections.append(f"\nKEY PROJECTS\n{projects}")

        if education:
            sections.append(f"\nEDUCATION & BACKGROUND\n{education}")

        raw_text = "\n\n".join(sections)

        # AI Enhancement if enabled and available
        if enhance and self.ollama.is_available():
            ai_res = self.ollama.generate(
                prompt=f"""You are an expert ATS resume writer. Polish the following resume text into a highly professional, high-impact resume format with clear section headings, active action verbs, and quantifiable bullet points where applicable. Keep all factual details (Name, Contact, Education, Skills, Experience) intact.

Resume Input:
{raw_text}

Output the polished ATS resume directly without conversational commentary.""",
                system_prompt="You are a professional ATS resume writer."
            )
            if ai_res.get("success") and ai_res.get("text"):
                raw_text = ai_res["text"].strip()

        # Combine experience and projects into experience field if projects present
        full_exp = experience
        if projects:
            full_exp = f"{experience}\n\nKey Projects:\n{projects}".strip() if experience else projects

        resume_id = self.db.save_resume(
            name=name,
            email=email,
            phone=phone,
            file_path="",
            raw_text=raw_text,
            skills=skills,
            experience=full_exp,
            education=education,
            linkedin=linkedin,
            github=github
        )

        self.db.log_agent_activity(
            "ResumeMind",
            f"Generated resume for '{name}'",
            "Completed",
            f"Included {len(skills)} skills and {len(full_exp)} chars of experience/projects"
        )

        active_resume = self.db.get_active_resume()
        score = self.score_resume(active_resume or {"raw_text": raw_text, "skills": skills, "experience": full_exp, "education": education, "email": email, "phone": phone, "linkedin": linkedin, "github": github})

        return {
            "success": True,
            "resume_id": resume_id,
            "resume": active_resume,
            "score": score
        }




