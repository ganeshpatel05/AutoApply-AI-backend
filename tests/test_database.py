"""Unit tests for SQLite Database Manager"""

import unittest
import tempfile
import os
from database.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def test_database_lifecycle(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = DatabaseManager(db_path=db_path)
            db.init_db()

            # Save Resume
            res_id = db.save_resume(
                name="Test User",
                email="test@example.com",
                skills=["Python", "SQL"]
            )
            self.assertGreater(res_id, 0)
            active = db.get_active_resume()
            self.assertEqual(active["name"], "Test User")
            self.assertIn("Python", active["skills"])

            # Insert Job
            job_id = db.insert_job(
                title="Software Engineer",
                company="TestCorp",
                location="Remote",
                description="Python & SQL role",
                ats_score=85.0
            )
            self.assertGreater(job_id, 0)

            # Create Application
            app_id = db.create_application(
                job_id=job_id,
                status="Saved",
                cover_letter="Test Cover Letter"
            )
            self.assertGreater(app_id, 0)

            # Update Status
            db.update_application_status(app_id, "Applied")
            app = db.get_application_by_id(app_id)
            self.assertEqual(app["status"], "Applied")

            # Check Stats
            stats = db.get_stats()
            self.assertEqual(stats["total_jobs"], 1)
            self.assertEqual(stats["total_apps"], 1)
            self.assertEqual(stats["avg_ats"], 85.0)

        finally:
            if 'db' in locals():
                db.close()
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except Exception:
                pass



if __name__ == "__main__":
    unittest.main()
