"""Unit tests for Resume Parser"""

import unittest
from tools.resume_parser import ResumeParser


class TestResumeParser(unittest.TestCase):
    def test_resume_parser_plain_text(self):
        parser = ResumeParser()
        sample_text = """
        John Doe
        Email: john.doe@example.com
        Phone: +91 9876543210
        LinkedIn: linkedin.com/in/johndoe
        GitHub: github.com/johndoe

        Technical Skills:
        Python, Java, React, SQL, Docker, Machine Learning

        Education:
        Master of Computer Applications (MCA) - 2024

        Experience:
        Software Developer Intern - Developed REST APIs using Python and Django.
        """

        data = parser.parse_text(sample_text)
        self.assertEqual(data["name"], "John Doe")
        self.assertEqual(data["email"], "john.doe@example.com")
        self.assertIn("python", [s.lower() for s in data["skills"]])
        self.assertGreater(data["word_count"], 10)



if __name__ == "__main__":
    unittest.main()
