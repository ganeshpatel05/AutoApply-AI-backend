"""AutoApply AI — Job Scraper & Sources Architecture
Clean job search abstraction with live scrapers and bundled demo data mode.
"""

import re
import time
import random
import requests
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from config.settings import SCRAPE_DELAY, MAX_JOBS


class JobSource(ABC):
    """Abstract base class for all job sources."""

    @abstractmethod
    def search(self, role: str, location: str = "", experience: str = "0") -> list[dict]:
        """Search jobs and return normalized list of job dicts."""
        pass


class DemoJobSource(JobSource):
    """Bundled sample job data source for offline/demonstration mode."""

    def search(self, role: str, location: str = "", experience: str = "0") -> list[dict]:
        companies = [
            ("TCS", "Tata Consultancy Services", "TCS Careers", "careers"),
            ("Infosys", "Infosys Limited", "LinkedIn", "linkedin"),
            ("Wipro", "Wipro Technologies", "Naukri.com", "naukri"),
            ("HCLTech", "HCL Technologies", "Indeed", "indeed"),
            ("Tech Mahindra", "Tech Mahindra Limited", "Wellfound", "wellfound"),
            ("Cognizant", "Cognizant Technology Solutions", "Glassdoor", "glassdoor"),
            ("Accenture", "Accenture India", "Accenture Careers", "careers"),
            ("Capgemini", "Capgemini India", "LinkedIn", "linkedin"),
        ]

        skills_pool = [
            "Python, Machine Learning, TensorFlow, SQL, Git",
            "Java, Spring Boot, Microservices, Docker, AWS",
            "React, Node.js, MongoDB, REST API, Git",
            "Data Science, Pandas, NumPy, Scikit-learn, Tableau",
            "Django, Flask, PostgreSQL, Redis, Linux",
            "Full Stack Development, React, Python, MySQL",
            "Angular, TypeScript, Node.js, GraphQL, Docker",
        ]

        jd_template = (
            "{role} Developer / Engineer\n\n"
            "We are hiring a talented {role} professional to join our team at {company}.\n\n"
            "Responsibilities:\n"
            "- Design, implement and maintain efficient software solutions\n"
            "- Collaborate with cross-functional development teams\n"
            "- Write clean, robust and testable code\n"
            "- Participate in design and code reviews\n\n"
            "Required Skills:\n"
            "{skills}\n\n"
            "Qualifications:\n"
            "- B.E. / B.Tech / MCA in Computer Science or IT\n"
            "- 0-2 years of relevant hands-on experience\n"
            "- Solid problem-solving and communication abilities\n\n"
            "Benefits: Competitive salary | Health insurance | Learning & Growth"
        )

        jobs = []
        locs = ["Bangalore", "Hyderabad", "Pune", "Chennai", "Mumbai", "Remote", "Noida"]
        for i, (short, full, src_name, platform) in enumerate(companies):
            skills = random.choice(skills_pool)
            job_loc = location if location else locs[i % len(locs)]
            role_slug = re.sub(r'[^a-zA-Z0-9]+', '-', role.lower()).strip('-') or "developer"
            short_slug = re.sub(r'[^a-zA-Z0-9]+', '-', short.lower()).strip('-')

            if platform == "linkedin":
                url = f"https://www.linkedin.com/jobs/view/{short_slug}-{role_slug}-{3902810 + i}"
            elif platform == "indeed":
                url = f"https://www.indeed.com/viewjob?jk={short_slug}{i+1}920"
            elif platform == "naukri":
                url = f"https://www.naukri.com/job-listings-{short_slug}-{role_slug}-{i+1}00224001"
            elif platform == "wellfound":
                url = f"https://wellfound.com/jobs/{short_slug}-{role_slug}-{i+1}"
            elif platform == "glassdoor":
                url = f"https://www.glassdoor.com/job-listing/{short_slug}-{role_slug}-JV_IC{294058 + i}.htm"
            else:
                url = f"https://careers.{short_slug}.com/jobs/{role_slug}-{i+1}"

            jobs.append({
                "title": f"{role} Developer" if "Developer" not in role and "Engineer" not in role else role,
                "company": full,
                "location": job_loc,
                "description": jd_template.format(role=role, company=full, skills=skills),
                "requirements": skills,
                "url": url,
                "source": src_name,
                "source_job_id": f"DEMO-{short}-{i+1}",
                "salary": "₹5.5L - ₹8.5L P.A.",
                "job_type": "Full-time",
                "company_type": "MNC (Multi National Company)",
                "is_mnc": True,
                "experience": f"{experience} years" if experience != "0" else "0-2 years",
            })
        return jobs


class PublicJobSource(JobSource):
    """Scrapes public job listings from available sites and public job APIs."""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    def search(self, role: str, location: str = "", experience: str = "0") -> list[dict]:
        session = requests.Session()
        session.headers.update(self.HEADERS)

        jobs = []
        seen_urls = set()

        # 1. Try Internshala live HTML scraping
        try:
            role_slug = role.lower().replace(" ", "-")
            url = f"https://internshala.com/jobs/{role_slug}-jobs"
            resp = session.get(url, timeout=6)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select(".internship_meta, .individual_internship")
                for card in cards:
                    title_el = card.select_one(".job-internship-name, .company-name a, h3")
                    comp_el = card.select_one(".company-name, .company")
                    loc_el = card.select_one(".location_link, .location")
                    link_el = (
                        card.select_one("a[href*='/job/detail']") or
                        card.select_one("a[href*='/jobs/detail']") or
                        card.select_one("a.view_detail_button") or
                        card.select_one("a[href]")
                    )

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = comp_el.get_text(strip=True) if comp_el else ""
                    loc = loc_el.get_text(strip=True) if loc_el else (location or "Remote")

                    raw_href = ""
                    if link_el and link_el.get("href"):
                        raw_href = link_el.get("href", "").strip()
                    elif card.get("data-href"):
                        raw_href = card.get("data-href", "").strip()

                    link = ""
                    if raw_href.startswith("http://") or raw_href.startswith("https://"):
                        link = raw_href
                    elif raw_href.startswith("/"):
                        link = f"https://internshala.com{raw_href}"

                    # Only accept specific job detail URLs, avoid search listing fallback
                    if link and ("/job/detail/" in link or "/jobs/detail/" in link):
                        pass
                    else:
                        link = ""

                    if title and company:
                        if company.startswith(title):
                            company = company[len(title):].strip()
                        if company.endswith("Actively hiring"):
                            company = company.replace("Actively hiring", "").strip()

                        if link and link in seen_urls:
                            continue
                        if link:
                            seen_urls.add(link)

                        jobs.append({
                            "title": title,
                            "company": company or "Tech Enterprise",
                            "location": loc,
                            "description": f"{title} position at {company}. Skills required for {role}.",
                            "requirements": f"{role}, Communication, Teamwork",
                            "url": link,
                            "source_url": link,
                            "apply_url": link,
                            "source": "Internshala",
                            "source_job_id": "",
                            "salary": "₹5.5L - ₹9.5L P.A.",
                            "job_type": "Full-time",
                            "experience": f"{experience} years",
                        })
        except Exception:
            pass

        # 2. Try Arbeitnow / Jobicy public open job API for live developer roles
        if len(jobs) < MAX_JOBS:
            try:
                api_url = "https://www.arbeitnow.com/api/job-board-api"
                resp = session.get(api_url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    role_keywords = role.lower().split()
                    for item in data:
                        job_title = item.get("title", "")
                        comp_name = item.get("company_name", "")
                        job_url = item.get("url", "").strip()
                        
                        # Match role keywords loosely
                        if any(kw in job_title.lower() for kw in role_keywords) or not role_keywords:
                            if job_url and job_url not in seen_urls:
                                seen_urls.add(job_url)
                                jobs.append({
                                    "title": job_title,
                                    "company": comp_name or "Tech Firm",
                                    "location": item.get("location", location or "Remote"),
                                    "description": BeautifulSoup(item.get("description", ""), "html.parser").get_text(strip=True)[:300],
                                    "requirements": ", ".join(item.get("tags", [])[:5]) or f"{role}, Git, Problem Solving",
                                    "url": job_url,
                                    "source_url": job_url,
                                    "apply_url": job_url,
                                    "source": "Arbeitnow",
                                    "source_job_id": str(item.get("slug", "")),
                                    "salary": "₹6.0L - ₹12.0L P.A.",
                                    "job_type": "Full-time",
                                    "experience": f"{experience} years",
                                })
                        if len(jobs) >= MAX_JOBS:
                            break
            except Exception:
                pass

        return jobs


class JobScraper:
    """Orchestrates job searching across sources with fallback to Demo Mode."""

    def __init__(self, demo_mode: bool = False):
        self.demo_mode = demo_mode
        self.demo_source = DemoJobSource()
        self.public_source = PublicJobSource()

    def search_jobs(self, role: str, location: str = "", experience: str = "0", demo_mode: bool = None) -> list[dict]:
        use_demo = self.demo_mode if demo_mode is None else demo_mode

        if use_demo:
            print("   [INFO] Using Demo Job Source")
            jobs = self.demo_source.search(role, location, experience)
        else:
            print(f"[SEARCH] Searching live jobs for: {role} in {location or 'All India'}")
            live_jobs = []
            try:
                live_jobs = self.public_source.search(role, location, experience)
            except Exception as e:
                print(f"   [WARNING] Live scraping error: {e}")

            if not live_jobs:
                print("   [INFO] Live source returned no jobs or was blocked. Returning empty list.")
                return []
            jobs = live_jobs[:MAX_JOBS]

        # Deduplication & Canonical URL normalization
        seen_keys = set()
        deduped_jobs = []

        for j in jobs:
            clean_url = (
                j.get("source_url") or
                j.get("sourceUrl") or
                j.get("original_url") or
                j.get("originalUrl") or
                j.get("url") or
                j.get("job_url") or
                j.get("jobUrl") or
                j.get("apply_url") or
                j.get("applyUrl") or
                j.get("link") or
                ""
            ).strip()

            # Unwrap google tracking/redirect link if present
            if "google.com/url?" in clean_url and "q=" in clean_url:
                try:
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(clean_url)
                    target = parse_qs(parsed.query).get("q", [""])[0]
                    if target:
                        clean_url = target.strip()
                except Exception:
                    pass

            dedup_key = f"{j.get('company','').lower()}|{j.get('title','').lower()}|{clean_url.lower()}"
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            j["url"] = clean_url
            j["job_url"] = clean_url
            j["source_url"] = clean_url
            j["apply_url"] = clean_url
            deduped_jobs.append(j)

        return deduped_jobs

