"""Integration tests for complete Multi-Agent Pipeline"""

import unittest
import tempfile
import os
from agents.orchestrator import AutoApplyOrchestrator
from database.db_manager import DatabaseManager


class TestPipeline(unittest.TestCase):
    def test_full_pipeline_demo_mode(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            db = DatabaseManager(db_path=db_path)
            db.init_db()
            orchestrator = AutoApplyOrchestrator(db)

            # Pre-populate active resume
            db.save_resume(
                name="Demo Candidate",
                email="candidate@demo.ai",
                skills=["Python", "Machine Learning", "SQL", "React", "Docker"],
                experience="1 year as Python Developer",
                education="MCA Computer Science"
            )

            # Run pipeline in Demo Mode
            res = orchestrator.run_pipeline(
                role="Python Developer",
                location="Bangalore",
                experience="1",
                demo_mode=True,
                generate_cover_letters_count=2
            )

            self.assertTrue(res["success"])
            self.assertGreater(len(res["jobs"]), 0)
            self.assertEqual(len(res["ranked_jobs"]), len(res["jobs"]))
            self.assertEqual(len(res["cover_letters"]), 2)
            self.assertEqual(len(res["applications"]), 2)
            self.assertEqual(res["resume"]["name"], "Demo Candidate")

            # Verify Database contents
            stats = db.get_stats()
            self.assertGreater(stats["total_jobs"], 0)
            self.assertEqual(stats["total_apps"], 2)

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
