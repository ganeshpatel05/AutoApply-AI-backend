"""AutoApply AI — Agent 2: Job Search Agent
Finds, normalizes, and stores job listings.
"""

from tools.job_scraper import JobScraper
from database.db_manager import DatabaseManager


class JobSearchAgent:
    """Agent responsible for discovering and saving job listings."""

    def __init__(self, db: DatabaseManager = None):
        self.scraper = JobScraper()
        self.db = db or DatabaseManager()

    def search_and_store(self, role: str, location: str = "", experience: str = "0", demo_mode: bool = False) -> list[dict]:
        """Search jobs from sources, store them in SQLite, and return normalized list."""
        jobs = self.scraper.search_jobs(role, location, experience, demo_mode=demo_mode)

        if not jobs:
            return []

        # Batch insert all jobs in a single transaction instead of N individual insert_job calls
        job_dicts = [
            {
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "description": job.get("description", job.get("jd_text", "")),
                "requirements": job.get("requirements", ""),
                "url": job.get("url") or job.get("job_url") or job.get("jobUrl") or job.get("source_url") or job.get("sourceUrl") or job.get("apply_url") or job.get("applyUrl") or "",
                "source_url": job.get("source_url") or job.get("url") or "",
                "apply_url": job.get("apply_url") or job.get("url") or "",
                "source": job.get("source", "Live"),
                "source_job_id": job.get("source_job_id", ""),
                "salary": job.get("salary", ""),
                "job_type": job.get("job_type", "Full-time"),
                "experience": job.get("experience", experience),
                "ats_score": job.get("ats_score", 0),
            }
            for job in jobs
        ]
        db_ids = self.db.batch_insert_jobs(job_dicts)

        stored_jobs = []
        for job, db_id in zip(jobs, db_ids):
            job_copy = job.copy()
            job_copy["id"] = db_id
            stored_jobs.append(job_copy)

        self.db.log_agent_activity(
            "Scout",
            f"Discovered and stored {len(stored_jobs)} jobs for role '{role}'",
            "Completed",
            f"Mode: {'Demo' if demo_mode else 'Live'} | Location: {location or 'All India'}"
        )

        return stored_jobs

