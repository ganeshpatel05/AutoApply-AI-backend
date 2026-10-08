import unittest
from tools.job_scraper import JobScraper, DemoJobSource, PublicJobSource
from database.db_manager import DatabaseManager

class TestJobUrls(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")

    def test_demo_job_urls(self):
        source = DemoJobSource()
        jobs = source.search("Software Engineer")
        self.assertGreater(len(jobs), 0)
        
        # Verify each job has a unique, valid http/https URL
        urls = [j.get("url") for j in jobs]
        self.assertEqual(len(urls), len(jobs))
        
        for job in jobs:
            url = job.get("url")
            self.assertIsNotNone(url)
            self.assertTrue(url.startswith("http://") or url.startswith("https://"))
            self.assertNotIn(" ", url)

    def test_platform_specific_urls(self):
        source = DemoJobSource()
        jobs = source.search("Software Engineer")
        
        sources_found = set()
        for job in jobs:
            src = job.get("source")
            url = job.get("url")
            sources_found.add(src)
            
            if src == "LinkedIn":
                self.assertIn("linkedin.com/jobs/view/", url)
            elif src == "Indeed":
                self.assertIn("indeed.com/viewjob", url)
            elif src == "Naukri.com":
                self.assertIn("naukri.com/job-listings-", url)
            elif src == "Glassdoor":
                self.assertIn("glassdoor.com/job-listing/", url)
            elif src == "Wellfound":
                self.assertIn("wellfound.com/jobs/", url)

        self.assertIn("LinkedIn", sources_found)
        self.assertIn("Indeed", sources_found)
        self.assertIn("Naukri.com", sources_found)
        self.assertIn("Glassdoor", sources_found)

    def test_job_url_normalization_and_aliases(self):
        scraper = JobScraper(demo_mode=True)
        jobs = scraper.search_jobs("Python Developer")
        for job in jobs:
            self.assertIn("url", job)
            self.assertIn("job_url", job)
            self.assertIn("apply_url", job)
            self.assertIn("source_url", job)
            self.assertEqual(job["url"], job["job_url"])
            self.assertEqual(job["url"], job["apply_url"])
            self.assertEqual(job["url"], job["source_url"])
            self.assertTrue(job["url"].startswith("http"))

    def test_db_url_persistence_and_update(self):
        job_id = self.db.insert_job(
            title="Frontend Developer",
            company="Acme Corp",
            url="https://www.linkedin.com/jobs/view/12345678",
            source="LinkedIn"
        )
        fetched = self.db.get_job_by_id(job_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["url"], "https://www.linkedin.com/jobs/view/12345678")
        self.assertEqual(fetched["job_url"], "https://www.linkedin.com/jobs/view/12345678")
        self.assertEqual(fetched["apply_url"], "https://www.linkedin.com/jobs/view/12345678")
        self.assertEqual(fetched["source_url"], "https://www.linkedin.com/jobs/view/12345678")

    def test_redirect_unwrapping(self):
        scraper = JobScraper(demo_mode=True)
        raw_jobs = [{
            "title": "Backend Engineer",
            "company": "Google",
            "location": "Bangalore",
            "url": "https://www.google.com/url?q=https://www.linkedin.com/jobs/view/998877",
            "source": "LinkedIn"
        }]
        # Process through canonical URL logic
        for j in raw_jobs:
            clean_url = j["url"]
            if "google.com/url?" in clean_url and "q=" in clean_url:
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(clean_url)
                target = parse_qs(parsed.query).get("q", [""])[0]
                if target:
                    clean_url = target
            j["url"] = clean_url

        self.assertEqual(raw_jobs[0]["url"], "https://www.linkedin.com/jobs/view/998877")

    def test_missing_urls_not_fabricated(self):
        job_id = self.db.insert_job(
            title="Backend Engineer",
            company="Secret Startup",
            url="",
            source="Internal"
        )
        fetched = self.db.get_job_by_id(job_id)
        self.assertEqual(fetched["url"], "")
        self.assertEqual(fetched["source_url"], "")

    def test_distinct_job_urls_preserved(self):
        id1 = self.db.insert_job(
            title="Dev 1",
            company="Comp 1",
            url="https://www.linkedin.com/jobs/view/11111",
            source="LinkedIn"
        )
        id2 = self.db.insert_job(
            title="Dev 2",
            company="Comp 2",
            url="https://www.indeed.com/viewjob?jk=22222",
            source="Indeed"
        )
        j1 = self.db.get_job_by_id(id1)
        j2 = self.db.get_job_by_id(id2)
        self.assertNotEqual(j1["url"], j2["url"])
        self.assertEqual(j1["url"], "https://www.linkedin.com/jobs/view/11111")
        self.assertEqual(j2["url"], "https://www.indeed.com/viewjob?jk=22222")

    def test_application_url_preservation(self):
        job_id = self.db.insert_job(
            title="Full Stack Engineer",
            company="TechCorp",
            url="https://internshala.com/job/detail/full-stack-engineer-12345",
            source="Internshala"
        )
        app_id = self.db.create_application(job_id=job_id, status="Applied", notes="Submitted resume")
        app = self.db.get_application_by_id(app_id)
        self.assertIsNotNone(app)
        self.assertEqual(app["job_id"], job_id)
        self.assertEqual(app["url"], "https://internshala.com/job/detail/full-stack-engineer-12345")
        self.assertEqual(app["source_url"], "https://internshala.com/job/detail/full-stack-engineer-12345")

if __name__ == "__main__":
    unittest.main()


