"""AutoApply AI — Resume Parser Tool
Extracts structured information from uploaded PDF resumes.
"""

import re
import json
import pdfplumber
import PyPDF2
from pathlib import Path
from utils.helpers import clean_text, extract_emails, extract_phone_numbers, common_tech_keywords


class ResumeParser:
    """Parses PDF resumes and extracts structured data."""

    def __init__(self):
        self.tech_keywords = common_tech_keywords()
        # Pre-compile keyword pattern for fast matching
        self._keyword_pattern = re.compile(
            r'\b(?:' + '|'.join(re.escape(kw) for kw in sorted(self.tech_keywords, key=len, reverse=True)) + r')\b'
        )

    # ─── Main Parse Entry Point ───────────────────────────────────────

    def parse_pdf(self, pdf_path: str) -> dict:
        """Parse a PDF resume and return structured data."""
        raw_text = self._extract_text(pdf_path)
        if not raw_text:
            raise ValueError(f"Could not extract text from: {pdf_path}")

        return {
            "raw_text":    raw_text,
            "name":        self._extract_name(raw_text),
            "email":       self._extract_email(raw_text),
            "phone":       self._extract_phone(raw_text),
            "skills":      self._extract_skills(raw_text),
            "experience":  self._extract_experience(raw_text),
            "education":   self._extract_education(raw_text),
            "linkedin":    self._extract_linkedin(raw_text),
            "github":      self._extract_github(raw_text),
            "word_count":  len(raw_text.split()),
        }

    def parse_text(self, text: str) -> dict:
        """Parse a plain-text resume."""
        return {
            "raw_text":    text,
            "name":        self._extract_name(text),
            "email":       self._extract_email(text),
            "phone":       self._extract_phone(text),
            "skills":      self._extract_skills(text),
            "experience":  self._extract_experience(text),
            "education":   self._extract_education(text),
            "linkedin":    self._extract_linkedin(text),
            "github":      self._extract_github(text),
            "word_count":  len(text.split()),
        }

    # ─── PDF Text Extraction ──────────────────────────────────────────

    def _extract_text(self, pdf_path: str) -> str:
        """Try pdfplumber first, fallback to PyPDF2."""
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
        except Exception:
            pass

        if not text.strip():
            try:
                with open(pdf_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += (page.extract_text() or "") + "\n"
            except Exception as e:
                raise ValueError(f"PDF extraction failed: {e}")

        return clean_text(text)

    # ─── Field Extractors ─────────────────────────────────────────────

    def _extract_name(self, text: str) -> str:
        """Extract and title-case candidate name accurately."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for line in lines[:5]:
            clean_line = re.sub(r'[\w\.-]+@[\w\.-]+', '', line)
            clean_line = re.sub(r'(?:https?://)?(?:www\.)?(?:linkedin|github)\.com\S*', '', clean_line, flags=re.IGNORECASE)
            clean_line = re.sub(r'[\+\d\-\(\)\s]{8,}', '', clean_line)
            clean_line = re.sub(r'\b(?:resume|cv|curriculum|vitae|profile|summary|contact|email|phone)\b', '', clean_line, flags=re.IGNORECASE).strip()
            
            words = clean_line.split()
            if 1 <= len(words) <= 4:
                title_keywords = {"software", "developer", "engineer", "full", "stack", "java", "python", "backend", "frontend", "web", "data", "intern", "manager", "lead", "senior", "junior"}
                if not any(w.lower() in title_keywords for w in words):
                    name = " ".join(words).title()
                    if len(name) >= 3:
                        return name

        first_chunk = text[:300]
        first_chunk = re.sub(r'[\w\.-]+@[\w\.-]+', '', first_chunk)
        first_chunk = re.sub(r'(?:https?://)?(?:www\.)?(?:linkedin|github)\.com\S*', '', first_chunk, flags=re.IGNORECASE)
        first_chunk = re.sub(r'[\+\d\-\(\)\s]{8,}', '', first_chunk)
        
        split_pattern = r'\b(?:Software|Developer|Java|Full|Stack|Engineer|Web|Data|Python|Backend|Frontend|Indore|Mumbai|Delhi|Bangalore|Pune|Hyderabad|India|USA|UK|PROFESSIONAL|SUMMARY|OBJECTIVE|EXPERIENCE|EDUCATION)\b'
        match = re.search(split_pattern, first_chunk, re.IGNORECASE)
        if match:
            name_part = first_chunk[:match.start()].strip()
            words = name_part.split()
            if 1 <= len(words) <= 4:
                name = " ".join(words).title()
                if len(name) >= 3:
                    return name
                    
        return "Candidate"

    def _extract_email(self, text: str) -> str:
        emails = extract_emails(text)
        return emails[0] if emails else ""

    def _extract_phone(self, text: str) -> str:
        from utils.helpers import extract_phone_numbers
        phones = extract_phone_numbers(text)
        return phones[0] if phones else ""

    def _extract_skills(self, text: str) -> list[str]:
        """Extract clean technical skills without section category labels."""
        text_lower = text.lower()
        found = []

        skills_section = ""
        patterns = [
            r"(?:technical\s+)?skills?\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|experience|projects|academic|\n)|\Z)",
            r"core\s+competencies?\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|experience|projects|\n)|\Z)",
            r"technologies?\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|experience|projects|\n)|\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                skills_section = match.group(1).lower()
                break

        search_text = (skills_section or text_lower)
        found = list(set(self._keyword_pattern.findall(search_text)))

        if skills_section:
            raw_skills = re.split(r'[,\|/\n•\-]', skills_section)
            for s in raw_skills:
                s = s.strip()
                if ':' in s:
                    s = s.split(':')[-1].strip()
                if 2 <= len(s) <= 35 and s not in found:
                    found.append(s)

        cleaned = []
        for item in found:
            if ':' in item:
                item = item.split(':')[-1].strip()
            item_clean = item.strip().title()
            if len(item_clean) >= 2 and item_clean not in cleaned:
                cleaned.append(item_clean)

        return cleaned[:30]

    def _extract_experience(self, text: str) -> str:
        """Extract experience and key project section text."""
        patterns = [
            r"(?:professional\s+|career\s+)?summary\s*[:\-]?\s*(.*?)(?=\n\s*(?:technical\s+skills|skills|education|projects|academic|certifications)|\Z)",
            r"(?:professional\s+|work\s+|employment\s+|career\s+|relevant\s+)?(?:experience|history|employment)\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|skills|projects|certifications|certificates|honors|publications|languages)|\Z)",
            r"(?:key\s+)?projects?\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|skills|certifications|certificates|honors|languages|\Z))"
        ]
        extracted = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match and len(match.group(1).strip()) > 20:
                extracted.append(match.group(1).strip())
        
        if extracted:
            combined = "\n\n".join(extracted)
            return combined[:3000]
        
        return text[:2000].strip()

    def _extract_education(self, text: str) -> str:
        """Extract education section text."""
        pattern = r"(?:education|academic\s+qualifications|academic\s+background|qualifications|education\s+&\s+training)\s*[:\-]?\s*(.*?)(?=\n\s*(?:experience|skills|projects|certifications|summary|\Z))"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match and len(match.group(1).strip()) > 10:
            return match.group(1).strip()[:1500]
            
        degrees = re.findall(r'(?:bachelor|master|bca|mca|b\.tech|m\.tech|btech|mtech|b\.sc|m\.sc|diploma)[^.\n]+', text, re.IGNORECASE)
        if degrees:
            return " | ".join([d.strip() for d in degrees[:4]])
        return ""

    def _extract_linkedin(self, text: str) -> str:
        match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
        return f"https://{match.group(0)}" if match else ""

    def _extract_github(self, text: str) -> str:
        match = re.search(r'github\.com/[\w\-]+', text, re.IGNORECASE)
        return f"https://{match.group(0)}" if match else ""

    def get_skills_text(self, resume_data: dict) -> str:
        """Return skills as a clean comma-separated string."""
        return ", ".join(resume_data.get("skills", []))

    def _extract_projects(self, text: str) -> list[dict]:
        """Extract individual projects with name, tech stack, and description."""
        patterns = [
            r"(?:key\s+|academic\s+|personal\s+)?projects?\s*[:\-]?\s*(.*?)(?=\n\s*(?:education|skills|experience|certifications|certificates|honors|languages|\Z))",
        ]
        projects_text = ""
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match and len(match.group(1).strip()) > 15:
                projects_text = match.group(1).strip()
                break

        if not projects_text:
            return []

        raw_chunks = [c.strip() for c in re.split(r'\n(?=[A-Z0-9][\w\s\-\:\.\(\)]+[\:\-]\s*|\n|•|\*|\d+\.)', projects_text) if c.strip()]
        projects = []

        for chunk in raw_chunks:
            lines = [l.strip() for l in chunk.split('\n') if l.strip()]
            if not lines:
                continue
            
            first_line = lines[0]
            first_line = re.sub(r'^[•\*\-\d\.\s]+', '', first_line).strip()
            
            tech_found = self._keyword_pattern.findall(chunk.lower())
            tech_clean = list(set([t.title() for t in tech_found]))
            
            if ':' in first_line:
                parts = first_line.split(':', 1)
                title = parts[0].strip()
                desc = parts[1].strip() + (" " + " ".join(lines[1:]) if len(lines) > 1 else "")
            else:
                title = first_line[:60]
                desc = " ".join(lines[1:]) if len(lines) > 1 else first_line

            if len(title) >= 3 and not any(kw in title.lower() for kw in ["education", "skills", "experience"]):
                projects.append({
                    "title": title,
                    "description": desc.strip()[:400],
                    "tech": tech_clean
                })

        return projects[:5]

    def _categorize_skills(self, skills: list[str]) -> dict:
        """Categorize skills into technical domains with null-safety."""
        langs = {"java", "python", "javascript", "typescript", "c++", "c#", "php", "ruby", "go", "golang", "rust", "sql", "html", "css", "kotlin", "swift", "r"}
        frameworks = {"react", "angular", "vue", "node", "nodejs", "node.js", "express", "django", "flask", "fastapi", "spring", "spring boot", "next.js", "nextjs", "redux", "tailwind", "bootstrap"}
        dbs = {"postgresql", "mysql", "mongodb", "sqlite", "redis", "oracle", "cassandra", "firebase", "dynamodb"}
        cloud = {"aws", "docker", "kubernetes", "gcp", "azure", "ci/cd", "jenkins", "git", "github", "linux"}
        
        result = {
            "programming_languages": [],
            "frameworks": [],
            "databases": [],
            "cloud_devops": [],
            "tools_other": []
        }
        safe_skills = skills if isinstance(skills, list) else []
        for s in safe_skills:
            if not s or not isinstance(s, str):
                continue
            sl = s.lower().strip()
            if sl in langs:
                result["programming_languages"].append(s)
            elif sl in frameworks:
                result["frameworks"].append(s)
            elif sl in dbs:
                result["databases"].append(s)
            elif sl in cloud:
                result["cloud_devops"].append(s)
            else:
                result["tools_other"].append(s)
        return result

    def get_structured_profile(self, resume_data: dict) -> dict:
        """Construct comprehensive candidate profile with strict null-safety."""
        if not isinstance(resume_data, dict):
            resume_data = {}

        raw_text = (resume_data.get("raw_text") or "").strip()
        name = (resume_data.get("name") or "").strip()
        if not name or name.lower() == "candidate":
            name = self._extract_name(raw_text)
            
        skills = resume_data.get("skills") if isinstance(resume_data.get("skills"), list) else []
        if not skills and raw_text:
            skills = self._extract_skills(raw_text)
            
        experience = (resume_data.get("experience") or "").strip()
        if not experience and raw_text:
            experience = self._extract_experience(raw_text)
            
        education = (resume_data.get("education") or "").strip()
        if not education and raw_text:
            education = self._extract_education(raw_text)
            
        projects = self._extract_projects(raw_text)
        categorized = self._categorize_skills(skills)
        
        return {
            "name": name if name and name.lower() != "candidate" else "Candidate",
            "email": (resume_data.get("email") or self._extract_email(raw_text) or "").strip(),
            "phone": (resume_data.get("phone") or self._extract_phone(raw_text) or "").strip(),
            "skills": skills,
            "categorized_skills": categorized,
            "experience": experience,
            "education": education,
            "projects": projects,
            "raw_text": raw_text
        }

    def resume_summary(self, resume_data: dict) -> str:
        """Create a detailed summary string of the resume for LLM input."""
        profile = self.get_structured_profile(resume_data)
        exp = profile['experience']
        edu = profile['education']
        return f"""Candidate Name: {profile['name']}
Email: {profile['email'] or 'N/A'}
Phone: {profile['phone'] or 'N/A'}
Technical Skills: {", ".join(profile['skills'])}
Categorized Skills: {json.dumps(profile['categorized_skills'])}
Projects: {json.dumps(profile['projects'])}

Work & Experience:
{exp[:2500]}

Education:
{edu[:1000]}""".strip()



