"""AutoApply AI — Multi-Agent Orchestrator
Coordinates all specialized agents in sequence:
Resume Agent → Job Search Agent → ATS Agent → Cover Letter Agent → Tracker Agent
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.resume_agent import ResumeAgent
from agents.job_search_agent import JobSearchAgent
from agents.ats_agent import ATSAgent
from agents.cover_letter_agent import CoverLetterAgent
from agents.tracker_agent import TrackerAgent
from database.db_manager import DatabaseManager


class AutoApplyOrchestrator:
    """Master Multi-Agent Orchestrator."""

    def __init__(self, db: DatabaseManager = None):
        self.db = db or DatabaseManager()
        self.db.init_db()
        self.resume_agent = ResumeAgent(self.db)
        self.job_search_agent = JobSearchAgent(self.db)
        self.ats_agent = ATSAgent(self.db)
        self.cover_letter_agent = CoverLetterAgent(self.db)
        self.tracker_agent = TrackerAgent(self.db)

    def run_pipeline(
        self,
        resume_pdf_path: str = None,
        role: str = "Software Developer",
        location: str = "",
        experience: str = "0",
        demo_mode: bool = False,
        generate_cover_letters_count: int = 3,
    ) -> dict:
        """
        Execute full end-to-end multi-agent pipeline.
        Returns structured dictionary with execution summary.
        """
        self.db.log_agent_activity("Orchestrator", f"Initiated job search & matching pipeline for '{role}'", "Running", f"Location: {location or 'All India'} | Demo: {demo_mode}")
        errors = []
        resume_data = None

        # Step 1: Resume Agent
        if resume_pdf_path:
            try:
                resume_data = self.resume_agent.process_pdf(resume_pdf_path)
            except Exception as e:
                errors.append(f"Resume Agent error: {str(e)}")

        if not resume_data:
            resume_data = self.resume_agent.get_active_resume()

        if not resume_data:
            self.db.log_agent_activity("Orchestrator", "Pipeline stopped - No active resume", "Error", "Upload resume required")
            return {
                "success": False,
                "resume": None,
                "jobs": [],
                "ranked_jobs": [],
                "cover_letters": [],
                "applications": [],
                "errors": ["No active resume found or uploaded. Please upload a resume first."]
            }

        # Step 2: Job Search Agent (Scout)
        jobs = []
        try:
            jobs = self.job_search_agent.search_and_store(
                role=role,
                location=location,
                experience=experience,
                demo_mode=demo_mode
            )
        except Exception as e:
            errors.append(f"Job Search Agent error: {str(e)}")

        if not jobs:
            self.db.log_agent_activity("Orchestrator", "Pipeline completed - No jobs discovered", "Completed", "0 jobs returned")
            return {
                "success": True,
                "resume": resume_data,
                "jobs": [],
                "ranked_jobs": [],
                "cover_letters": [],
                "applications": [],
                "errors": errors + ["No job listings discovered."]
            }

        # Step 3: ATS Agent (Matcher)
        ranked_jobs = []
        try:
            ranked_jobs = self.ats_agent.evaluate_jobs(resume_data, jobs)
        except Exception as e:
            errors.append(f"ATS Agent error: {str(e)}")
            ranked_jobs = jobs

        # Step 4: Cover Letter Agent & Step 5: Tracker Agent for top N jobs
        cover_letters = []
        applications = []
        top_n_jobs = ranked_jobs[:generate_cover_letters_count]

        def _process_single_job(job):
            """Generate cover letter and track application for a single job."""
            cl_res = self.cover_letter_agent.generate_cover_letter(resume_data, job)
            cl_entry = {
                "job_id": job.get("id"),
                "job_title": job.get("title"),
                "company": job.get("company"),
                "content": cl_res["content"],
                "used_ai": cl_res["used_ai"]
            }
            app_id = self.tracker_agent.add_to_tracker(
                job_id=job.get("id"),
                status="Saved",
                cover_letter=cl_res["content"],
                notes=f"Auto-added by pipeline. ATS Score: {job.get('ats_score', 0)}%"
            )
            return cl_entry, app_id

        # Parallel execution: generate all cover letters concurrently
        with ThreadPoolExecutor(max_workers=min(3, max(1, len(top_n_jobs)))) as executor:
            future_to_job = {
                executor.submit(_process_single_job, job): job
                for job in top_n_jobs
            }
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    cl_entry, app_id = future.result()
                    cover_letters.append(cl_entry)
                    applications.append(app_id)
                except Exception as e:
                    errors.append(f"Pipeline step error for job {job.get('title')}: {str(e)}")

        self.db.log_agent_activity(
            "Orchestrator",
            f"Completed multi-agent pipeline: {len(jobs)} jobs scored, {len(cover_letters)} cover letters generated",
            "Completed" if not errors else "Warnings",
            f"Errors: {len(errors)}"
        )

        return {
            "success": len(errors) == 0,
            "resume": resume_data,
            "jobs": jobs,
            "ranked_jobs": ranked_jobs,
            "cover_letters": cover_letters,
            "applications": applications,
            "errors": errors
        }

