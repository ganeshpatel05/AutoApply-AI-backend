"""AutoApply AI — Agent 4: Cover Letter Agent
Generates professional, highly personalized, job-specific cover letters grounded in candidate experience.
Supports local Ollama LLM execution with multi-step validation and smart grounded fallback.
"""

import re
import json
from tools.ollama_client import OllamaClient
from tools.resume_parser import ResumeParser
from tools.ats_scorer import ATSScorer
from database.db_manager import DatabaseManager


def validate_cover_letter(content: str, candidate_name: str, job_title: str, company: str, resume_skills: list[str]) -> tuple[bool, list[str]]:
    """
    Validates generated cover letter quality and adherence to constraints.
    Returns (is_valid, list_of_error_strings).
    """
    errors = []
    if not content or not content.strip():
        return False, ["Cover letter content is empty"]

    content_lower = content.lower()

    # 1. Check for bracketed/curly placeholders
    placeholders = ["[name]", "[company]", "[job title]", "[recipient]", "[date]", "[insert]", "<name>", "{company}", "[your name]", "[job]", "[city]", "[hiring manager]", "[company name]"]
    for p in placeholders:
        if p in content_lower:
            errors.append(f"Contains leftover placeholder string '{p}'")

    # 2. Check for generic candidate placeholder when real name exists
    if candidate_name and candidate_name.lower() != "candidate":
        if "dear hiring team at candidate" in content_lower or "sincerely,\ncandidate" in content_lower or "sincerely,\n candidate" in content_lower:
            errors.append("Uses placeholder name 'Candidate' instead of candidate's real name")

    # 3. Word count check (130 - 550 words target)
    words = [w for w in content.split() if w.strip()]
    if len(words) < 130:
        errors.append(f"Content is too short ({len(words)} words; min 130 words required)")
    elif len(words) > 550:
        errors.append(f"Content is too long ({len(words)} words; max 550 words allowed)")

    # 4. Keyword dumping check (e.g. 5+ consecutive capitalized/comma skills without verbs)
    dump_match = re.search(r'(?:[A-Z][a-zA-B0-9\+\#\.]+(?:,\s*|\s+and\s+)){4,}[A-Z][a-zA-B0-9\+\#\.]+', content)
    if dump_match:
        errors.append("Contains raw comma-separated list of keywords without natural context")

    return (len(errors) == 0, errors)


class CoverLetterAgent:
    """Agent responsible for crafting truthful, personalized cover letters."""

    def __init__(self, db: DatabaseManager = None):
        self.ollama = OllamaClient()
        self.db = db or DatabaseManager()
        self.resume_parser = ResumeParser()
        self.ats_scorer = ATSScorer()

    def generate_cover_letter(
        self,
        resume_data: dict,
        job: dict,
        tone: str = "Professional",
        length: str = "Standard",
        variation: int = 1
    ) -> dict:
        """
        Generate a personalized cover letter grounded in candidate experience and job match analysis.
        Returns complete response dictionary including content, match_summary, candidate_info, job_info.
        """
        # 1. Extract Structured Candidate Profile & Job Match Analysis
        if not isinstance(job, dict):
            job = {}

        profile = self.resume_parser.get_structured_profile(resume_data)
        candidate_name = (profile.get("name") or "Candidate").strip()
        if not candidate_name or candidate_name.lower() == "candidate":
            prof = self.db.get_profile()
            if prof and prof.get("full_name"):
                candidate_name = prof["full_name"].strip()
                profile["name"] = candidate_name

        job_title = (job.get("title") or "Software Developer").strip()
        company = (job.get("company") or "Target Company").strip()
        jd_text = (job.get("description") or job.get("jd_text") or "").strip()

        match_res = self.ats_scorer.analyze_match(resume_data, job)

        # Build context strings for prompt with null safety
        strong_matches = match_res.get("strong_matches") if isinstance(match_res.get("strong_matches"), list) else []
        skills = profile.get("skills") if isinstance(profile.get("skills"), list) else []
        strong_matches_str = ", ".join(str(s) for s in strong_matches) if strong_matches else ", ".join(str(s) for s in skills[:5])
        
        selected_projects = match_res.get("selected_projects") if isinstance(match_res.get("selected_projects"), list) else []
        projects_formatted = []
        for p in selected_projects:
            if not isinstance(p, dict):
                continue
            title = (p.get("title") or "Project").strip()
            desc = (p.get("description") or "").strip()
            tech = p.get("tech") if isinstance(p.get("tech"), list) else []
            p_tech = f" (Tech: {', '.join(str(t) for t in tech)})" if tech else ""
            projects_formatted.append(f"- Project Title: {title}{p_tech}\n  Description: {desc}")
        projects_str = "\n".join(projects_formatted) if projects_formatted else "No specific projects detailed in resume."

        word_count_target = "200-280 words" if length == "Short" else ("380-480 words" if length == "Detailed" else "260-360 words")
        
        variation_instruction = ""
        if variation > 1:
            variation_instruction = f"VARIATION MODE ({variation}): Vary the opening sentence, paragraph emphasis, and phrasing from standard templates while remaining 100% truthful."

        prompt = f"""You are an expert executive career writer. Write a highly personalized, professional cover letter for the candidate applying to the specified job.

JOB DETAILS:
Job Title: {job_title}
Company Name: {company}
Job Description Overview:
{jd_text[:1200]}

CANDIDATE PROFILE:
Candidate Name: {candidate_name}
Education: {profile.get('education', 'N/A')}
Top Technical Skills: {", ".join(str(s) for s in skills[:12])}
Strong Skill Matches for Job: {strong_matches_str}
Selected Relevant Projects:
{projects_str}
Experience Summary:
{str(profile.get('experience') or '')[:1200]}

WRITING INSTRUCTIONS:
1. Write specifically for the EXACT job title "{job_title}" at "{company}".
2. Use candidate's actual name "{candidate_name}". Do NOT use "Candidate" or placeholders like [NAME], [COMPANY], [JOB TITLE].
3. Word count target: {word_count_target} across 4 to 5 concise paragraphs.
4. Tone: {tone}.
5. {variation_instruction}
6. STRICT ANTI-HALLUCINATION RULE:
   - Ground every statement strictly in the provided candidate profile.
   - NEVER invent companies, job roles, metrics, degrees, certifications, or technologies not present in the resume.
7. NO KEYWORD DUMPING:
   - Do NOT produce raw lists of skills (e.g. "I have skills in A, B, C, D, E").
   - Instead, incorporate skills naturally into meaningful sentences describing actual work/project contributions.
8. Paragraph Structure:
   - Paragraph 1: Personalized opening specifying interest in {job_title} at {company}, stating candidate's background ({candidate_name}).
   - Paragraph 2: Relevant experience explaining what candidate actually built/did and why it aligns with the role.
   - Paragraph 3: Highlight 1-2 relevant projects from the candidate's resume, tech used, and specific contributions.
   - Paragraph 4: Explicit job alignment connecting candidate strengths to job description requirements.
   - Paragraph 5: Professional closing requesting an interview opportunity.
9. Ending: End strictly with 'Sincerely,' on one line followed by '{candidate_name}' on the next line.

Return ONLY the final complete cover letter text."""

        system_prompt = f"You are Scribe, an executive career assistant crafting customized, truthful {tone} cover letters."

        used_ai = False
        model_used = ""
        err_msg = ""
        final_content = ""

        # 2. Attempt Ollama AI Generation with Validation & Retry
        if self.ollama.is_available():
            ai_res = self.ollama.generate(prompt=prompt, system_prompt=system_prompt)
            if ai_res["success"] and ai_res["text"]:
                raw_text = ai_res["text"].strip()
                if raw_text.startswith("```") and raw_text.endswith("```"):
                    lines = raw_text.split("\n")
                    if len(lines) > 2:
                        raw_text = "\n".join(lines[1:-1]).strip()

                is_valid, v_errors = validate_cover_letter(raw_text, candidate_name, job_title, company, profile["skills"])
                if is_valid:
                    final_content = raw_text
                    used_ai = True
                    model_used = ai_res["model"]
                else:
                    # Single corrective retry with specific validation feedback
                    retry_prompt = f"{prompt}\n\nPREVIOUS GENERATION HAD ISSUES:\n" + "\n".join(f"- {e}" for e in v_errors) + "\nPlease rewrite the cover letter addressing these exact issues."
                    retry_res = self.ollama.generate(prompt=retry_prompt, system_prompt=system_prompt)
                    if retry_res["success"] and retry_res["text"]:
                        retry_text = retry_res["text"].strip()
                        if retry_text.startswith("```") and retry_text.endswith("```"):
                            lines = retry_text.split("\n")
                            if len(lines) > 2:
                                retry_text = "\n".join(lines[1:-1]).strip()
                        is_valid_2, _ = validate_cover_letter(retry_text, candidate_name, job_title, company, profile["skills"])
                        if is_valid_2:
                            final_content = retry_text
                            used_ai = True
                            model_used = retry_res["model"]

            if not final_content:
                err_msg = ai_res.get("error") or "LLM generation failed validation checks"
        else:
            err_msg = f"Ollama LLM server is not reachable at {self.ollama.base_url}"

        # 3. Fallback to High-Quality Smart Grounded Generator if AI output unavailable or invalid
        if not final_content:
            used_ai = False
            model_used = "Smart Grounded Engine"
            final_content = self._generate_grounded_fallback(
                profile=profile,
                match_res=match_res,
                job_title=job_title,
                company=company,
                tone=tone,
                length=length,
                variation=variation
            )

        # 4. Save to database if job_id exists
        job_id = job.get("id") or job.get("db_id")
        if job_id:
            try:
                self.db.save_cover_letter(job_id=job_id, content=final_content)
            except Exception as e:
                print(f"[CoverLetterAgent] Error saving to DB: {e}")

        # 5. Log Activity
        self.db.log_agent_activity(
            "Scribe",
            f"Generated {tone} cover letter for {job_title} at {company}",
            "Completed" if used_ai else "Fallback",
            f"Model: {model_used} | Length: {length} | Error: {err_msg if err_msg else 'None'}"
        )

        return {
            "content": final_content,
            "used_ai": used_ai,
            "model": model_used,
            "error": err_msg,
            "match_summary": match_res,
            "candidate_info": {
                "name": candidate_name,
                "skills_count": len(profile.get("skills", [])),
                "resume_analyzed": True
            },
            "job_info": {
                "id": job_id,
                "title": job_title,
                "company": company,
                "location": job.get("location", "")
            }
        }

    def _generate_grounded_fallback(
        self,
        profile: dict,
        match_res: dict,
        job_title: str,
        company: str,
        tone: str = "Professional",
        length: str = "Standard",
        variation: int = 1
    ) -> str:
        """Ground-truth rule-based cover letter builder using candidate's actual projects & skills."""
        if not isinstance(profile, dict):
            profile = {}
        if not isinstance(match_res, dict):
            match_res = {}

        name = (profile.get("name") or "Candidate").strip()
        if not name or name.lower() == "candidate":
            prof = self.db.get_profile()
            if prof and prof.get("full_name"):
                name = prof["full_name"].strip()
            else:
                name = "Applicant"

        education = (profile.get("education") or "").strip()
        deg_str = ""
        if education:
            deg_found = re.findall(r'\b(?:MCA|BCA|B\.Tech|M\.Tech|BTech|MTech|B\.Sc|M\.Sc|Bachelor|Master|Computer Science)[^,\.\n]*', education, re.IGNORECASE)
            if deg_found:
                deg_str = f" with a background in {deg_found[0].strip()}"

        strong_matches = match_res.get("strong_matches") if isinstance(match_res.get("strong_matches"), list) else []
        top_skills = profile.get("skills") if isinstance(profile.get("skills"), list) else []
        skills_formatted = ", ".join(str(s) for s in strong_matches[:4]) if strong_matches else (", ".join(str(s) for s in top_skills[:4]) if top_skills else "software engineering")

        selected_projects = match_res.get("selected_projects") if isinstance(match_res.get("selected_projects"), list) else []
        project_para = ""
        if selected_projects and isinstance(selected_projects[0], dict):
            proj = selected_projects[0]
            proj_title = (proj.get("title") or "Software Application").strip()
            proj_desc = (proj.get("description") or "").strip()
            proj_tech_list = proj.get("tech") if isinstance(proj.get("tech"), list) else []
            proj_tech = ", ".join(str(t) for t in proj_tech_list)
            tech_phrase = f" using {proj_tech}" if proj_tech else ""
            if proj_desc:
                project_para = f"During my work on {proj_title}{tech_phrase}, I led development on key application components. {proj_desc[:220]} This project enabled me to tackle technical challenges and deliver reliable software logic."
            else:
                project_para = f"In my recent project, {proj_title}{tech_phrase}, I designed and implemented scalable application features. This experience strengthened my ability to build clean code, optimize performance, and adhere to engineering standards."
        else:
            exp_text = (profile.get("experience") or "").strip()
            if exp_text:
                clean_exp = exp_text[:250].rsplit('.', 1)[0] + "."
                project_para = f"Throughout my software development endeavors, I have focused on writing clean, maintainable code and building end-to-end applications. {clean_exp}"
            else:
                project_para = f"Throughout my technical background, I have focused on writing scalable code, building RESTful APIs, and implementing database-driven solutions."

        if variation % 3 == 1:
            p1 = f"I am excited to submit my application for the {job_title} position at {company}. As a software developer{deg_str} with core expertise in {skills_formatted}, I am eager to contribute to your engineering team's ongoing goals."
            p2 = f"My technical experience centers on building scalable software components, integrating application APIs, and managing relational databases. Having developed solutions with {skills_formatted}, I have built a practical foundation in software engineering best practices that directly aligns with the responsibilities of the {job_title} role."
            p3 = project_para
            p4 = f"The {job_title} position at {company} offers an ideal opportunity to apply my background in {skills_formatted}. I am particularly interested in {company}'s focus on engineering quality and would value the chance to bring my technical skills and dedication to your team."
            p5 = f"Thank you for considering my application. I welcome the opportunity to discuss how my background and hands-on project experience can support {company}'s development priorities."
        elif variation % 3 == 2:
            p1 = f"I am writing to express my strong interest in joining {company} as a {job_title}. With hands-on background in {skills_formatted}{deg_str}, I am confident in my ability to deliver meaningful technical contributions to your software initiatives."
            p2 = f"Over the course of my software development work, I have focused on architecting reliable backend services, optimizing data workflows, and maintaining clean code standards. My experience working with {skills_formatted} aligns closely with the core technical requirements outlined for the {job_title} role."
            p3 = project_para
            p4 = f"What excites me about the {job_title} role at {company} is the opportunity to tackle technical challenges alongside a talented team. My background in {skills_formatted} equips me to quickly get up to speed and contribute effectively."
            p5 = f"I would welcome the opportunity to interview and share more details about my technical experience. Thank you for your time and consideration."
        else:
            p1 = f"Please accept my application for the {job_title} role at {company}. As a dedicated developer{deg_str} with proficiency in {skills_formatted}, I am keen to contribute to {company}'s software engineering initiatives."
            p2 = f"My experience encompasses full-stack software development, RESTful API design, and database integration. Working with {skills_formatted} has enabled me to build robust applications while adhering to modern software design patterns."
            p3 = project_para
            p4 = f"The requirements for the {job_title} position strongly match my technical toolkit, particularly in relation to {skills_formatted}. I am eager to bring this background to {company} and collaborate on building high-impact software solutions."
            p5 = f"Thank you for reviewing my application. I look forward to the possibility of discussing how my technical background aligns with your engineering goals."

        return f"""Dear Hiring Team at {company},

{p1}

{p2}

{p3}

{p4}

{p5}

Sincerely,
{name}"""
