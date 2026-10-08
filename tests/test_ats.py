"""Unit tests for ATS Scorer"""

import unittest
from tools.ats_scorer import ATSScorer


class TestATSScorer(unittest.TestCase):
    def test_ats_scorer_high_match(self):
        scorer = ATSScorer()
        resume_data = {
            "raw_text": "Experienced Python Developer with expertise in Django, FastAPI, SQL, Docker, AWS, and REST APIs.",
            "skills": ["python", "django", "fastapi", "sql", "docker", "aws", "rest api"],
            "education": "B.E. Computer Science",
            "experience": "3 years as Python Developer working with Docker and AWS"
        }

        jd_text = """
        Python Developer Position
        Responsibilities: Develop REST APIs using Python and Django. Deploy on AWS with Docker.
        Requirements: Python, Django, SQL, Docker, AWS. 2+ years experience. B.E/B.Tech required.
        """

        res = scorer.score(resume_data, jd_text)
        self.assertGreaterEqual(res["score"], 75.0)
        self.assertIn(res["recommendation"], ["Strong Match", "Excellent Match"])
        self.assertIn("python", res["matched_keywords"])

    def test_ats_scorer_low_match(self):
        scorer = ATSScorer()
        resume_data = {
            "raw_text": "Graphic Designer with experience in Photoshop, Illustrator, and UI/UX design.",
            "skills": ["photoshop", "illustrator", "figma"],
            "education": "Bachelor of Fine Arts",
            "experience": "2 years as Graphic Designer"
        }

        jd_text = """
        Senior Java Spring Boot Engineer. Must have 5+ years experience in Microservices, Kubernetes, and Oracle SQL.
        """

        res = scorer.score(resume_data, jd_text)
        self.assertLess(res["score"], 50.0)
        self.assertEqual(res["recommendation"], "Low Match")


if __name__ == "__main__":
    unittest.main()
