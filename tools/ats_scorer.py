"""AutoApply AI — ATS (Applicant Tracking System) Scorer
Deterministic multi-component ATS scoring algorithm:
1. Skill match (40%)
2. Keyword match (25%)
3. Experience match (15%)
4. Education match (10%)
5. Text similarity (10%)

Performance-optimized: pre-compiled regex, resume caching, cached vector norms.
"""

import re
import math
from collections import Counter
from utils.helpers import common_tech_keywords


class ATSScorer:
    """Calculates ATS match score between resume and job description."""

    def __init__(self):
        self.tech_keywords = set(common_tech_keywords())
        patterns = []
        for kw in sorted(self.tech_keywords, key=len, reverse=True):
            escaped = re.escape(kw)
            left_b = r'\b' if kw[0].isalnum() else r'(?:^|\s)'
            right_b = r'\b' if kw[-1].isalnum() else r'(?:$|\s|[.,!?;])'
            patterns.append(f"{left_b}{escaped}{right_b}")
        self._keyword_pattern = re.compile("|".join(patterns), re.IGNORECASE)

    def _precompute_resume(self, resume_data: dict | str) -> dict:
        """Pre-compute and cache all resume-derived data to avoid redundant processing across jobs."""
        if isinstance(resume_data, str):
            resume_text = resume_data
            resume_skills = set(self._extract_keywords(resume_text))
            education_text = resume_text
            experience_text = resume_text
        else:
            resume_text = resume_data.get("raw_text", "")
            skills_list = resume_data.get("skills", [])
            resume_skills = set(s.lower() for s in skills_list).union(self._extract_keywords(resume_text))
            education_text = resume_data.get("education", "")
            experience_text = resume_data.get("experience", "")

        # Pre-compute keyword set for experience
        exp_keywords = self._extract_keywords(experience_text) if experience_text else set()

        # Pre-compute cosine similarity vector for resume text
        resume_words = re.findall(r'\w+', resume_text.lower())
        resume_vec = Counter(resume_words)
        resume_norm = math.sqrt(sum(v**2 for v in resume_vec.values()))

        return {
            "resume_text": resume_text,
            "resume_skills": resume_skills,
            "education_text": education_text,
            "experience_text": experience_text,
            "exp_keywords": exp_keywords,
            "resume_vec": resume_vec,
            "resume_norm": resume_norm,
        }

    def _score_with_cache(self, cache: dict, job: dict) -> dict:
        """Score a single job using pre-computed resume cache."""
        jd_text = job.get("description", job.get("jd_text", ""))
        if not jd_text or not jd_text.strip():
            job_copy = job.copy()
            job_copy.update({"ats_score": 0.0, "recommendation": "Low Match",
                             "matched_keywords": [], "missing_keywords": []})
            return job_copy

        jd_kw = self._extract_keywords(jd_text)
        jd_tech = jd_kw & self.tech_keywords

        resume_skills = cache["resume_skills"]

        # Component 1: Skill Matching (40%)
        matched_skills = resume_skills & (jd_tech if jd_tech else jd_kw)
        target_skill_count = max(1, len(jd_tech) if jd_tech else len(jd_kw))
        skill_ratio = min(1.0, len(matched_skills) / target_skill_count)
        skill_score = skill_ratio * 40.0

        # Component 2: General Keyword Matching (25%)
        matched_all = resume_skills & jd_kw
        missing_all = jd_kw - matched_all
        kw_ratio = min(1.0, len(matched_all) / max(1, len(jd_kw)))
        keyword_score = kw_ratio * 25.0

        # Component 3: Experience Matching (15%)
        exp_score = self._evaluate_experience_cached(cache["experience_text"], cache["exp_keywords"], jd_text, jd_kw) * 15.0

        # Component 4: Education Matching (10%)
        edu_score = self._evaluate_education(cache["education_text"], jd_text) * 10.0

        # Component 5: Cosine Similarity (10%) — uses cached resume vector
        sim_score = self._cosine_similarity_cached(cache["resume_vec"], cache["resume_norm"], jd_text) * 10.0

        total_score = min(100.0, round(skill_score + keyword_score + exp_score + edu_score + sim_score, 1))

        if total_score >= 80:
            recommendation = "Excellent Match"
        elif total_score >= 65:
            recommendation = "Strong Match"
        elif total_score >= 50:
            recommendation = "Moderate Match"
        else:
            recommendation = "Low Match"

        job_copy = job.copy()
        job_copy["ats_score"] = total_score
        job_copy["recommendation"] = recommendation
        job_copy["matched_keywords"] = sorted(list(matched_all))
        job_copy["missing_keywords"] = sorted(list(missing_all))[:15]
        return job_copy

    def score(self, resume_data: dict | str, jd_text: str) -> dict:
        """
        Compute comprehensive 5-component ATS score (0-100).
        """
        if isinstance(resume_data, str):
            resume_text = resume_data
            resume_skills = set(self._extract_keywords(resume_text))
            education_text = resume_text
            experience_text = resume_text
        else:
            resume_text = resume_data.get("raw_text", "")
            skills_list = resume_data.get("skills", [])
            resume_skills = set([s.lower() for s in skills_list]).union(self._extract_keywords(resume_text))
            education_text = resume_data.get("education", "")
            experience_text = resume_data.get("experience", "")

        if not jd_text or not jd_text.strip():
            return {
                "score": 0.0,
                "breakdown": {"skill_score": 0, "keyword_score": 0, "exp_score": 0, "edu_score": 0, "sim_score": 0},
                "matched_keywords": [],
                "missing_keywords": [],
                "recommendation": "Low Match",
            }

        jd_kw = self._extract_keywords(jd_text)
        jd_tech = jd_kw & self.tech_keywords

        # Component 1: Skill Matching (40%)
        matched_skills = resume_skills & (jd_tech if jd_tech else jd_kw)
        target_skill_count = max(1, len(jd_tech) if jd_tech else len(jd_kw))
        skill_ratio = min(1.0, len(matched_skills) / target_skill_count)
        skill_score = skill_ratio * 40.0

        # Component 2: General Keyword Matching (25%)
        matched_all = resume_skills & jd_kw
        missing_all = jd_kw - matched_all
        kw_ratio = min(1.0, len(matched_all) / max(1, len(jd_kw)))
        keyword_score = kw_ratio * 25.0

        # Component 3: Experience Matching (15%)
        exp_score = self._evaluate_experience(experience_text, jd_text) * 15.0

        # Component 4: Education Matching (10%)
        edu_score = self._evaluate_education(education_text, jd_text) * 10.0

        # Component 5: Text Cosine Similarity (10%)
        sim_score = self._cosine_similarity(resume_text, jd_text) * 10.0

        total_score = min(100.0, round(skill_score + keyword_score + exp_score + edu_score + sim_score, 1))

        # Recommendation rating
        if total_score >= 80:
            recommendation = "Excellent Match"
        elif total_score >= 65:
            recommendation = "Strong Match"
        elif total_score >= 50:
            recommendation = "Moderate Match"
        else:
            recommendation = "Low Match"

        return {
            "score": total_score,
            "recommendation": recommendation,
            "breakdown": {
                "skill_score": round(skill_score, 1),
                "keyword_score": round(keyword_score, 1),
                "exp_score": round(exp_score, 1),
                "edu_score": round(edu_score, 1),
                "sim_score": round(sim_score, 1),
            },
            "matched_keywords": sorted(list(matched_all)),
            "missing_keywords": sorted(list(missing_all))[:15],
        }

    def _extract_keywords(self, text: str) -> set[str]:
        text_lower = text.lower()
        # Single regex pass instead of 65+ individual re.search calls
        keywords = set(self._keyword_pattern.findall(text_lower))

        stopwords = {
            "the", "and", "for", "with", "are", "have", "has", "will", "that",
            "this", "from", "your", "our", "you", "not", "but", "was", "were",
            "they", "their", "its", "can", "also", "able", "what", "when",
            "how", "any", "all", "more", "into", "over", "than", "then",
            "some", "such", "each", "both", "while", "should", "must",
            "using", "used", "use", "work", "working", "team", "role"
        }

        words = re.findall(r'\b[a-z][a-z0-9\+\#]{2,}\b', text_lower)
        for word in words:
            if word not in stopwords and len(word) >= 3:
                keywords.add(word)

        return keywords

    def _evaluate_experience(self, exp_text: str, jd_text: str) -> float:
        """Score experience alignment from 0.0 to 1.0."""
        if not exp_text:
            return 0.3  # Baseline if resume experience text isn't explicit
        exp_text_lower = exp_text.lower()
        jd_lower = jd_text.lower()

        # Check for years requirement
        years_req = re.search(r'(\d+)\s*\+?\s*years?', jd_lower)
        if years_req:
            req_years = int(years_req.group(1))
            cand_years = re.search(r'(\d+)\s*\+?\s*years?', exp_text_lower)
            if cand_years:
                found_years = int(cand_years.group(1))
                if found_years >= req_years:
                    return 1.0
                return max(0.4, found_years / req_years)

        # Keyword alignment in experience
        exp_kws = self._extract_keywords(exp_text_lower)
        jd_kws = self._extract_keywords(jd_lower)
        overlap = len(exp_kws & jd_kws)
        return min(1.0, max(0.5, overlap / max(1, len(jd_kws))))

    def _evaluate_experience_cached(self, exp_text: str, exp_keywords: set, jd_text: str, jd_kw: set) -> float:
        """Score experience alignment using pre-computed experience keywords."""
        if not exp_text:
            return 0.3
        exp_text_lower = exp_text.lower()
        jd_lower = jd_text.lower()

        years_req = re.search(r'(\d+)\s*\+?\s*years?', jd_lower)
        if years_req:
            req_years = int(years_req.group(1))
            cand_years = re.search(r'(\d+)\s*\+?\s*years?', exp_text_lower)
            if cand_years:
                found_years = int(cand_years.group(1))
                if found_years >= req_years:
                    return 1.0
                return max(0.4, found_years / req_years)

        overlap = len(exp_keywords & jd_kw)
        return min(1.0, max(0.5, overlap / max(1, len(jd_kw))))

    def _evaluate_education(self, edu_text: str, jd_text: str) -> float:
        """Score education alignment from 0.0 to 1.0."""
        degrees = ["mca", "b.tech", "btech", "b.e", "be", "b.sc", "bsc", "m.tech", "mtech", "master", "bachelor", "computer science"]
        jd_lower = jd_text.lower()
        edu_lower = edu_text.lower()

        req_degrees = [d for d in degrees if d in jd_lower]
        if not req_degrees:
            return 0.8  # No specific requirement stated

        has_degree = any(d in edu_lower for d in req_degrees)
        return 1.0 if has_degree else 0.5

    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """Compute term frequency cosine similarity between two texts."""
        words1 = re.findall(r'\w+', text1.lower())
        words2 = re.findall(r'\w+', text2.lower())

        vec1 = Counter(words1)
        vec2 = Counter(words2)

        intersection = set(vec1.keys()) & set(vec2.keys())
        numerator = sum([vec1[x] * vec2[x] for x in intersection])

        sum1 = sum([vec1[x]**2 for x in vec1.keys()])
        sum2 = sum([vec2[x]**2 for x in vec2.keys()])
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0
        return float(numerator) / denominator

    def _cosine_similarity_cached(self, resume_vec: Counter, resume_norm: float, jd_text: str) -> float:
        """Compute cosine similarity using pre-computed resume vector and norm."""
        if not resume_norm:
            return 0.0
        jd_words = re.findall(r'\w+', jd_text.lower())
        jd_vec = Counter(jd_words)

        intersection = set(resume_vec.keys()) & set(jd_vec.keys())
        numerator = sum(resume_vec[x] * jd_vec[x] for x in intersection)

        jd_norm = math.sqrt(sum(v**2 for v in jd_vec.values()))
        denominator = resume_norm * jd_norm

        if not denominator:
            return 0.0
        return float(numerator) / denominator

    def rank_jobs(self, resume_data: dict | str, jobs: list[dict]) -> list[dict]:
        """Rank jobs with pre-computed resume cache for maximum performance."""
        cache = self._precompute_resume(resume_data)
        scored = [self._score_with_cache(cache, job) for job in jobs]
        scored.sort(key=lambda x: x["ats_score"], reverse=True)
        return scored

    def analyze_match(self, resume_data: dict, job: dict) -> dict:
        """
        Perform detailed 4-category match analysis between resume and job description.
        """
        from tools.resume_parser import ResumeParser
        parser = ResumeParser()
        profile = parser.get_structured_profile(resume_data) if isinstance(resume_data, dict) else parser.parse_text(str(resume_data or ""))

        if not isinstance(job, dict):
            job = {}

        jd_text = (job.get("description") or job.get("jd_text") or job.get("title") or "").strip()
        ats_res = self.score(resume_data, jd_text)

        jd_kws = self._extract_keywords(jd_text)
        skills = profile.get("skills") if isinstance(profile.get("skills"), list) else []
        cand_skills = set(s.lower() for s in skills if isinstance(s, str))

        strong_matches = [s for s in skills if isinstance(s, str) and s.lower() in jd_kws]
        jd_tech = jd_kws & self.tech_keywords
        missing_skills = sorted(list(jd_tech - cand_skills))[:8]

        soft_keywords = {"agile", "api", "rest", "problem solving", "communication", "testing", "debugging", "teamwork", "git", "ci/cd", "system architecture", "database management", "cloud"}
        transferable = [s for s in skills if isinstance(s, str) and (s.lower() in soft_keywords or (s.lower() in jd_kws and s not in strong_matches))]
        
        projects = profile.get("projects") if isinstance(profile.get("projects"), list) else []
        scored_projects = []
        for p in projects:
            if not isinstance(p, dict):
                continue
            title = (p.get("title") or "").strip()
            desc = (p.get("description") or "").strip()
            tech = p.get("tech") if isinstance(p.get("tech"), list) else []
            p_text = f"{title} {desc} {' '.join(str(t) for t in tech)}".lower()
            p_kws = set(re.findall(r'\w+', p_text))
            overlap = len(p_kws & jd_kws)
            scored_projects.append((overlap, p))
            
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        selected_projects = [sp[1] for sp in scored_projects[:2]]

        return {
            "score": ats_res.get("score", 0.0),
            "recommendation": ats_res.get("recommendation", "Low Match"),
            "strong_matches": strong_matches[:10] if strong_matches else [s.title() for s in skills[:5] if isinstance(s, str)],
            "partial_matches": [m.title() for m in ats_res.get("matched_keywords", []) if isinstance(m, str) and m.title() not in strong_matches][:6],
            "transferable_skills": list(dict.fromkeys(transferable))[:6],
            "missing_skills": [m.title() for m in missing_skills if isinstance(m, str)],
            "selected_projects": selected_projects
        }


