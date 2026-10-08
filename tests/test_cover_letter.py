"""AutoApply AI — Test Suite for Cover Letter Generation Pipeline
Tests personalized generation, Resume-JD match integration, project selection, anti-hallucination, and validation.
"""

import unittest
from agents.cover_letter_agent import CoverLetterAgent, validate_cover_letter
from tools.resume_parser import ResumeParser
from tools.ats_scorer import ATSScorer
from database.db_manager import DatabaseManager


class TestCoverLetter(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db = DatabaseManager(db_path=self.tmp_db.name)
        self.db.init_db()

        self.java_resume = {
            "name": "Alex Mercer",
            "email": "alex.mercer@example.com",
            "phone": "555-0192",
            "skills": ["Java", "Spring Boot", "PostgreSQL", "REST APIs", "Maven", "Git", "JUnit", "SQL"],
            "education": "Bachelor of Technology in Computer Science, 2022",
            "experience": "Software Engineer at TechCorp (2022-Present). Developed RESTful backend APIs using Java and Spring Boot. Managed PostgreSQL databases and wrote complex SQL queries. Conducted unit testing with JUnit.",
            "raw_text": """
Alex Mercer
alex.mercer@example.com | 555-0192

TECHNICAL SKILLS:
Java, Spring Boot, PostgreSQL, REST APIs, Maven, Git, JUnit, SQL

PROJECTS:
Inventory Management System: Built a Java Spring Boot backend API with PostgreSQL database to handle stock tracking.
Payment Gateway Service: Implemented secure REST API endpoints for processing payment transactions.

EDUCATION:
Bachelor of Technology in Computer Science, 2022
            """
        }

        self.react_resume = {
            "name": "Sarah Connor",
            "email": "sarah.connor@example.com",
            "phone": "555-0144",
            "skills": ["React", "TypeScript", "JavaScript", "Redux", "Tailwind CSS", "HTML5", "CSS3", "Vite"],
            "education": "Master of Computer Applications (MCA), 2023",
            "experience": "Frontend Developer at WebCraft (2023-Present). Built responsive web user interfaces using React and TypeScript. State management with Redux and UI styling using Tailwind CSS.",
            "raw_text": """
Sarah Connor
sarah.connor@example.com | 555-0144

SKILLS:
React, TypeScript, JavaScript, Redux, Tailwind CSS, HTML5, CSS3, Vite

PROJECTS:
Analytics Dashboard UI: Designed and built an interactive React dashboard with TypeScript and Redux.
E-Commerce Frontend: Developed a modern storefront web application with Tailwind CSS and React.

EDUCATION:
Master of Computer Applications (MCA), 2023
            """
        }

        self.java_job = {
            "id": 101,
            "title": "Backend Java Developer",
            "company": "Enterprise Software Solutions",
            "description": "Looking for a Backend Java Developer to build RESTful microservices, integrate with PostgreSQL databases, and write high-quality Spring Boot application logic.",
            "location": "Remote"
        }

        self.react_job = {
            "id": 102,
            "title": "Frontend React Developer",
            "company": "PixelCraft Studios",
            "description": "We are seeking a Frontend React Developer skilled in TypeScript, React, and Redux to build state-of-the-art interactive web applications.",
            "location": "New York, NY"
        }

        self.data_analyst_job = {
            "id": 103,
            "title": "Data Analyst",
            "company": "DataInsights Inc",
            "description": "Looking for a Data Analyst to work with SQL queries, database reports, data visualization, and analytical problem solving.",
            "location": "Chicago, IL"
        }

        self.aws_job = {
            "id": 104,
            "title": "Cloud Backend Engineer",
            "company": "CloudScale Cloud",
            "description": "Role requires extensive hands-on experience deploying microservices to AWS Cloud (S3, EC2, Lambda) and Docker containerization.",
            "location": "Remote"
        }

    def tearDown(self):
        import os
        try:
            if hasattr(self, "tmp_db") and os.path.exists(self.tmp_db.name):
                os.remove(self.tmp_db.name)
        except Exception:
            pass

    def test_1_java_developer_java_resume(self):
        """Test 1: Java Developer + Java resume -> Emphasizes Java & backend experience."""
        agent = CoverLetterAgent(db=self.db)
        res = agent.generate_cover_letter(self.java_resume, self.java_job)
        content = res["content"]

        self.assertIn("Alex Mercer", content)
        self.assertIn("Backend Java Developer", content)
        self.assertIn("Enterprise Software Solutions", content)
        self.assertTrue("Java" in content or "Spring Boot" in content)

    def test_2_react_developer_react_resume(self):
        """Test 2: React Developer + React resume -> Emphasizes React & frontend experience."""
        agent = CoverLetterAgent(db=self.db)
        res = agent.generate_cover_letter(self.react_resume, self.react_job)
        content = res["content"]

        self.assertIn("Sarah Connor", content)
        self.assertIn("Frontend React Developer", content)
        self.assertIn("PixelCraft Studios", content)
        self.assertTrue("React" in content or "TypeScript" in content)

    def test_3_data_analyst_with_software_resume(self):
        """Test 3: Data Analyst + Software dev resume -> Emphasizes transferable skills (SQL, database management)."""
        agent = CoverLetterAgent(db=self.db)
        res = agent.generate_cover_letter(self.java_resume, self.data_analyst_job)
        content = res["content"]

        self.assertIn("Alex Mercer", content)
        self.assertIn("Data Analyst", content)
        self.assertIn("DataInsights Inc", content)
        self.assertTrue("SQL" in content or "database" in content.lower() or "PostgreSQL" in content)

    def test_4_job_requires_aws_resume_lacks_aws(self):
        """Test 4: Job requires AWS but resume doesn't mention AWS -> Must NOT claim AWS experience."""
        agent = CoverLetterAgent(db=self.db)
        res = agent.generate_cover_letter(self.java_resume, self.aws_job)
        content = res["content"]

        self.assertTrue(any(s.lower() == "aws" for s in res["match_summary"]["missing_skills"]))
        self.assertNotIn("expert in aws", content.lower())
        self.assertNotIn("extensive aws", content.lower())

    def test_5_project_selection(self):
        """Test 5: Resume contains multiple projects -> Selects most relevant projects."""
        parser = ResumeParser()
        profile = parser.get_structured_profile(self.java_resume)

        matcher = ATSScorer()
        match_analysis = matcher.analyze_match(self.java_resume, self.java_job)

        selected = match_analysis["selected_projects"]
        self.assertGreater(len(selected), 0)
        titles = [p["title"].lower() for p in selected]
        self.assertTrue(any("inventory" in t or "payment" in t for t in titles))

    def test_6_different_jobs_same_resume(self):
        """Test 6: Different job titles with the same resume -> Cover letters meaningfully change."""
        agent = CoverLetterAgent(db=self.db)
        res_java = agent.generate_cover_letter(self.java_resume, self.java_job)
        res_analyst = agent.generate_cover_letter(self.java_resume, self.data_analyst_job)

        self.assertNotEqual(res_java["content"], res_analyst["content"])
        self.assertIn("Backend Java Developer", res_java["content"])
        self.assertIn("Data Analyst", res_analyst["content"])

    def test_7_different_resumes_same_job(self):
        """Test 7: Different resumes with the same job -> Cover letters meaningfully change according to candidate."""
        agent = CoverLetterAgent(db=self.db)
        res_alex = agent.generate_cover_letter(self.java_resume, self.java_job)
        res_sarah = agent.generate_cover_letter(self.react_resume, self.java_job)

        self.assertNotEqual(res_alex["content"], res_sarah["content"])
        self.assertIn("Alex Mercer", res_alex["content"])
        self.assertIn("Sarah Connor", res_sarah["content"])

    def test_8_validation_checks(self):
        """Test 8: Validate post-generation validation checks."""
        valid_text = """Dear Hiring Team at TechCorp,

I am writing to express my strong interest in the Backend Developer position at TechCorp. As a software engineer with a background in Computer Science, I am eager to contribute to your engineering goals.

My technical background centers on building RESTful API services and managing database operations. Having developed backend solutions with Java and PostgreSQL, I have built a practical foundation in clean code architecture.

During my work on the Payment Gateway project, I implemented secure application logic and optimized API performance. This project allowed me to solve complex technical problems and ensure clean software design.

The Backend Developer role at TechCorp matches my background in software engineering. I welcome the opportunity to discuss how my technical experience can support your development goals.

Sincerely,
Alex Mercer"""

        is_valid, errors = validate_cover_letter(valid_text, "Alex Mercer", "Backend Developer", "TechCorp", ["Java", "PostgreSQL"])
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        invalid_text = "Dear Hiring Team at Co 9, I am Candidate applying for [JOB TITLE] at [COMPANY]."
        is_valid_bad, bad_errors = validate_cover_letter(invalid_text, "Alex Mercer", "Backend Developer", "TechCorp", [])
        self.assertFalse(is_valid_bad)
        self.assertGreater(len(bad_errors), 0)


if __name__ == "__main__":
    unittest.main()

