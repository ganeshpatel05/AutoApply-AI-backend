"""AutoApply AI — Agent 5: Tracker Agent
Maintains job application lifecycle state and coordinates optional email submissions.
"""

from tools.email_sender import EmailSender
from database.db_manager import DatabaseManager


class TrackerAgent:
    """Agent responsible for maintaining application state across SQLite database."""

    def __init__(self, db: DatabaseManager = None):
        self.email_sender = EmailSender()
        self.db = db or DatabaseManager()

    def add_to_tracker(self, job_id: int, status: str = "Saved", cover_letter: str = "", notes: str = "") -> int:
        """Add job to application tracker or update existing record."""
        app_id = self.db.create_application(
            job_id=job_id,
            status=status,
            cover_letter=cover_letter,
            notes=notes
        )
        self.db.log_agent_activity("Tracker", f"Added job ID #{job_id} to application tracker", "Completed", f"Initial Status: {status}")
        return app_id

    def update_status(self, app_id: int, status: str, notes: str = None):
        """Update status of an application."""
        self.db.update_application_status(app_id=app_id, status=status, notes=notes)
        self.db.log_agent_activity("Tracker", f"Updated application #{app_id} status to '{status}'", "Completed", f"Notes: {notes or 'None'}")

    def send_application_email(self, app_id: int, recipient_email: str, applicant_name: str, resume_path: str = None) -> dict:
        """Send email application via SMTP and update status to Applied."""
        app = self.db.get_application_by_id(app_id)
        if not app:
            return {"success": False, "message": "Application record not found."}

        res = self.email_sender.send_application(
            to_email=recipient_email,
            applicant_name=applicant_name,
            job_title=app.get("job_title", "Software Developer"),
            company=app.get("company", "Company"),
            cover_letter=app.get("cover_letter", ""),
            resume_path=resume_path
        )

        if res["success"]:
            self.db.mark_email_sent(app_id, email_recipient=recipient_email)
            self.db.log_agent_activity("Tracker", f"Sent application email to {recipient_email}", "Completed", f"Job: {app.get('job_title')}")
        else:
            self.db.log_agent_activity("Tracker", f"Failed to send email to {recipient_email}", "Error", res.get("message", ""))

        return res

