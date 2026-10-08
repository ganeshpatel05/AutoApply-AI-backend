"""AutoApply AI — Test Suite for Analytics Engine & DB Metrics Calculations
Tests get_stats, get_ats_details, get_conversion_details, and edge cases.
"""

import os
import unittest
import tempfile
from database.db_manager import DatabaseManager


class TestAnalyticsEngine(unittest.TestCase):

    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db = DatabaseManager(db_path=self.tmp_db.name)
        self.db.init_db()

    def tearDown(self):
        try:
            if os.path.exists(self.tmp_db.name):
                os.remove(self.tmp_db.name)
        except Exception:
            pass

    def test_empty_database_analytics(self):
        """Test analytics calculations on an empty database (handles zero division cleanly)."""
        stats = self.db.get_stats()
        self.assertEqual(stats["total_jobs"], 0)
        self.assertEqual(stats["total_apps"], 0)
        self.assertEqual(stats["avg_ats"], 0.0)

        ats_details = self.db.get_ats_details()
        self.assertEqual(ats_details["average_ats"], 0.0)
        self.assertEqual(ats_details["total_scored_jobs"], 0)
        self.assertEqual(len(ats_details["scored_jobs"]), 0)

        conv_details = self.db.get_conversion_details()
        self.assertEqual(conv_details["conversion_rates"]["interview_rate"], 0.0)
        self.assertEqual(conv_details["conversion_rates"]["offer_rate"], 0.0)

    def test_populated_analytics_calculations(self):
        """Test ATS average, distribution, and conversion rates with sample jobs & applications."""
        # Insert sample jobs with ATS scores
        j1 = self.db.insert_job(
            title="Senior Backend Engineer",
            company="Google",
            url="https://google.com/jobs/1",
            ats_score=92.5,
            matched_keywords=["Python", "FastAPI", "Docker"],
            missing_keywords=["Kubernetes"],
            is_saved=1
        )
        j2 = self.db.insert_job(
            title="Frontend Developer",
            company="Microsoft",
            url="https://microsoft.com/jobs/2",
            ats_score=75.0,
            matched_keywords=["React", "TypeScript"],
            missing_keywords=["Tailwind"],
            is_saved=0
        )
        j3 = self.db.insert_job(
            title="Full Stack Engineer",
            company="Amazon",
            url="https://amazon.com/jobs/3",
            ats_score=60.0,
            matched_keywords=["Node.js", "React"],
            missing_keywords=["AWS"],
            is_saved=1
        )

        # Create applications across pipeline stages
        app1 = self.db.create_application(job_id=j1, status="Applied")
        app2 = self.db.create_application(job_id=j2, status="Interview")
        app3 = self.db.create_application(job_id=j3, status="Offer")

        # Verify get_stats
        stats = self.db.get_stats()
        self.assertEqual(stats["total_jobs"], 3)
        self.assertEqual(stats["saved_jobs"], 2)
        self.assertEqual(stats["total_apps"], 3)
        self.assertEqual(stats["applied_apps"], 1)
        self.assertEqual(stats["interviews"], 1)
        self.assertEqual(stats["offers"], 1)
        self.assertAlmostEqual(stats["avg_ats"], 75.8, places=1)

        # Verify get_ats_details
        ats_details = self.db.get_ats_details()
        self.assertEqual(ats_details["total_scored_jobs"], 3)
        self.assertEqual(ats_details["distribution"]["90_100"], 1)
        self.assertEqual(ats_details["distribution"]["70_79"], 1)
        self.assertEqual(ats_details["distribution"]["60_69"], 1)
        self.assertEqual(len(ats_details["top_matched_keywords"]), 6)

        # Verify get_conversion_details
        conv_details = self.db.get_conversion_details()
        # 1 interview for 1 applied app => 100.0% interview rate
        self.assertEqual(conv_details["conversion_rates"]["interview_rate"], 100.0)
        # 1 offer for 1 applied app => 100.0% offer rate
        self.assertEqual(conv_details["conversion_rates"]["offer_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
