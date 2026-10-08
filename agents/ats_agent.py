"""AutoApply AI — Agent 3: ATS Agent
Scores jobs against active resume using multi-component algorithm and updates database.
"""

from tools.ats_scorer import ATSScorer
from database.db_manager import DatabaseManager


class ATSAgent:
    """Agent responsible for analyzing and scoring candidate resume against job descriptions."""

    def __init__(self, db: DatabaseManager = None):
        self.scorer = ATSScorer()
        self.db = db or DatabaseManager()

    def evaluate_jobs(self, resume_data: dict | str, jobs: list[dict]) -> list[dict]:
        """Score a list of jobs, update SQLite database, and return ranked jobs."""
        scored_jobs = self.scorer.rank_jobs(resume_data, jobs)

        # Batch update all ATS scores in a single transaction instead of N individual calls
        updates = [
            {
                "job_id": job["id"],
                "ats_score": job["ats_score"],
                "matched": job.get("matched_keywords", []),
                "missing": job.get("missing_keywords", [])
            }
            for job in scored_jobs if job.get("id")
        ]
        if updates:
            self.db.batch_update_ats(updates)

        self.db.log_agent_activity(
            "Matcher",
            f"Evaluated & ranked {len(scored_jobs)} jobs against active resume",
            "Completed",
            f"Top match score: {scored_jobs[0]['ats_score']:.0f}%" if scored_jobs else "No jobs"
        )

        return scored_jobs

    def evaluate_single_job(self, resume_data: dict | str, job: dict) -> dict:
        """Score a single job against resume."""
        res = self.scorer.score(resume_data, job.get("description", job.get("jd_text", "")))
        job_copy = job.copy()
        job_copy["ats_score"] = res["score"]
        job_copy["recommendation"] = res["recommendation"]
        job_copy["matched_keywords"] = res["matched_keywords"]
        job_copy["missing_keywords"] = res["missing_keywords"]
        job_copy["breakdown"] = res.get("breakdown", {})

        if "id" in job_copy and job_copy["id"]:
            self.db.update_job_ats(
                job_id=job_copy["id"],
                ats_score=res["score"],
                matched=res["matched_keywords"],
                missing=res["missing_keywords"]
            )

        self.db.log_agent_activity(
            "Matcher",
            f"Evaluated match for '{job.get('title')}' at '{job.get('company')}'",
            "Completed",
            f"Match Score: {res['score']:.1f}% ({res['recommendation']})"
        )

        return job_copy

