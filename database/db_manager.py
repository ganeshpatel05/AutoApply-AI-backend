"""AutoApply AI — Complete Database Manager (SQLite)
Provides parameterized CRUD operations and schema management.
Performance-optimized: persistent connection, WAL mode, batch operations, consolidated queries.
"""

import sqlite3
import json
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from config.settings import DB_PATH


import os

class DatabaseManager:
    """Manages all SQLite database operations for AutoApply AI."""
    _initialized_paths = set()
    _db_lock = threading.RLock()

    def __init__(self, db_path: str = None):
        self.db_path = str(db_path or DB_PATH)
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.db_path = "/tmp/autoapply.db"
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a persistent connection with optimized pragmas."""
        if self._conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10,
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Performance pragmas
            if os.getenv("VERCEL"):
                conn.execute("PRAGMA journal_mode=DELETE")
            else:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")
            conn.execute("PRAGMA busy_timeout=10000")
            conn.execute("PRAGMA temp_store=MEMORY")
            self._conn = conn
            self.init_db()
        return self._conn

    def close(self):
        """Close database connection cleanly."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __del__(self):
        self.close()


    @contextmanager
    def _connect(self):
        with DatabaseManager._db_lock:
            conn = self._get_conn()
            if conn.in_transaction:
                yield conn
            else:
                try:
                    yield conn
                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

    # ─── Schema Initialization ────────────────────────────────────────

    def init_db(self):
        """Create all required tables according to architecture spec."""
        resolved = str(Path(self.db_path).resolve())
        if self.db_path != ":memory:" and resolved in DatabaseManager._initialized_paths:
            return
        with self._connect() as conn:
            conn.executescript("""
                -- Profiles table
                CREATE TABLE IF NOT EXISTS profiles (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name       TEXT NOT NULL,
                    email           TEXT,
                    phone           TEXT,
                    location        TEXT,
                    target_roles    TEXT,
                    experience      TEXT,
                    education       TEXT,
                    linkedin        TEXT,
                    github          TEXT,
                    skills          TEXT,
                    theme_pref      TEXT DEFAULT 'light',
                    created_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );

                -- Resumes table
                CREATE TABLE IF NOT EXISTS resumes (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    email       TEXT,
                    phone       TEXT,
                    file_path   TEXT,
                    raw_text    TEXT,
                    skills      TEXT,
                    experience  TEXT,
                    education   TEXT,
                    linkedin    TEXT,
                    github      TEXT,
                    is_active   INTEGER DEFAULT 1,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                -- Jobs table
                CREATE TABLE IF NOT EXISTS jobs (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    title               TEXT NOT NULL,
                    company             TEXT NOT NULL,
                    location            TEXT,
                    description         TEXT,
                    requirements        TEXT,
                    url                 TEXT,
                    source              TEXT,
                    source_job_id       TEXT,
                    job_hash            TEXT UNIQUE,
                    salary              TEXT,
                    job_type            TEXT,
                    company_type        TEXT DEFAULT 'MNC (Multi National Company)',
                    is_mnc              INTEGER DEFAULT 1,
                    experience          TEXT,
                    ats_score           REAL DEFAULT 0,
                    matched_keywords    TEXT,
                    missing_keywords    TEXT,
                    is_saved            INTEGER DEFAULT 0,
                    created_at          TEXT DEFAULT (datetime('now')),
                    updated_at          TEXT DEFAULT (datetime('now'))
                );

                -- Applications table
                CREATE TABLE IF NOT EXISTS applications (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id          INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                    status          TEXT DEFAULT 'Saved',
                    cover_letter    TEXT,
                    resume_used     TEXT,
                    email           TEXT,
                    email_sent      INTEGER DEFAULT 0,
                    notes           TEXT,
                    applied_at      TEXT DEFAULT (datetime('now')),
                    updated_at      TEXT DEFAULT (datetime('now'))
                );

                -- Cover Letters table
                CREATE TABLE IF NOT EXISTS cover_letters (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id      INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
                    content     TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                -- Agent Logs table
                CREATE TABLE IF NOT EXISTS agent_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name  TEXT NOT NULL,
                    action      TEXT NOT NULL,
                    status      TEXT DEFAULT 'Completed',
                    details     TEXT,
                    created_at  TEXT DEFAULT (datetime('now'))
                );

                -- Indexes for optimization
                CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title);
                CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
                CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location);
                CREATE INDEX IF NOT EXISTS idx_jobs_ats_score ON jobs(ats_score);
                CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);
                CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
                CREATE INDEX IF NOT EXISTS idx_apps_job_id ON applications(job_id);
                CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at);
                -- Performance: composite index for dedup lookups
                CREATE INDEX IF NOT EXISTS idx_jobs_source_sid ON jobs(source, source_job_id);
                -- Performance: index for stats aggregation
                CREATE INDEX IF NOT EXISTS idx_apps_email_sent ON applications(email_sent);
            """)

            # Migration for existing databases
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN company_type TEXT DEFAULT 'MNC (Multi National Company)'")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN is_mnc INTEGER DEFAULT 1")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN source_url TEXT")
            except Exception:
                pass
            try:
                conn.execute("ALTER TABLE jobs ADD COLUMN apply_url TEXT")
            except Exception:
                pass

        DatabaseManager._initialized_paths.add(resolved)

    def reset_db(self):
        """Reset and recreate all tables."""
        with self._connect() as conn:
            conn.executescript("""
                DROP TABLE IF EXISTS agent_logs;
                DROP TABLE IF EXISTS applications;
                DROP TABLE IF EXISTS cover_letters;
                DROP TABLE IF EXISTS jobs;
                DROP TABLE IF EXISTS resumes;
                DROP TABLE IF EXISTS profiles;
            """)
        DatabaseManager._initialized = False
        self.init_db()

    # ─── Profiles CRUD ───────────────────────────────────────────────

    def save_profile(self, full_name: str, email: str = "", phone: str = "", location: str = "",
                     target_roles: str = "", experience: str = "", education: str = "",
                     linkedin: str = "", github: str = "", skills: list = None, theme_pref: str = "light") -> int:
        skills_json = json.dumps(skills or [])
        with self._connect() as conn:
            existing = conn.execute("SELECT id FROM profiles LIMIT 1").fetchone()
            if existing:
                conn.execute(
                    """UPDATE profiles SET
                       full_name=?, email=?, phone=?, location=?, target_roles=?, experience=?, education=?,
                       linkedin=?, github=?, skills=?, theme_pref=?, updated_at=datetime('now')
                       WHERE id=?""",
                    (full_name, email, phone, location, target_roles, experience, education,
                     linkedin, github, skills_json, theme_pref, existing["id"])
                )
                return existing["id"]
            else:
                cur = conn.execute(
                    """INSERT INTO profiles
                       (full_name, email, phone, location, target_roles, experience, education, linkedin, github, skills, theme_pref)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (full_name, email, phone, location, target_roles, experience, education, linkedin, github, skills_json, theme_pref)
                )
                return cur.lastrowid

    def get_profile(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM profiles LIMIT 1").fetchone()
            if row:
                d = dict(row)
                try:
                    d["skills"] = json.loads(d["skills"]) if d.get("skills") else []
                except Exception:
                    d["skills"] = []
                return d
            return None

    def update_theme(self, theme: str):
        with self._connect() as conn:
            conn.execute("UPDATE profiles SET theme_pref=?", (theme,))

    # ─── Resumes CRUD ────────────────────────────────────────────────

    def save_resume(self, name: str, email: str = "", phone: str = "",
                    file_path: str = "", raw_text: str = "", skills: list = None,
                    experience: str = "", education: str = "",
                    linkedin: str = "", github: str = "") -> int:
        skills_json = json.dumps(skills or [])
        with self._connect() as conn:
            # Set all previous resumes as inactive
            conn.execute("UPDATE resumes SET is_active=0")
            cur = conn.execute(
                """INSERT INTO resumes
                   (name, email, phone, file_path, raw_text, skills, experience, education, linkedin, github, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (name, email, phone, file_path, raw_text, skills_json, experience, education, linkedin, github)
            )
            return cur.lastrowid

    def get_active_resume(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM resumes WHERE is_active=1 ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                # Fallback to most recent
                row = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC LIMIT 1").fetchone()
            if row:
                d = dict(row)
                try:
                    d["skills"] = json.loads(d["skills"]) if d.get("skills") else []
                except Exception:
                    d["skills"] = []
                return d
            return None

    def get_all_resumes(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["skills"] = json.loads(d["skills"]) if d.get("skills") else []
                except Exception:
                    d["skills"] = []
                results.append(d)
            return results

    # ─── Jobs CRUD & Deduplication ───────────────────────────────────

    def _generate_job_hash(self, company: str, title: str, url: str) -> str:
        key = f"{company.strip().lower()}|{title.strip().lower()}|{url.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def insert_job(self, title: str, company: str, location: str = "",
                   description: str = "", requirements: str = "", url: str = "",
                   source: str = "Live", source_job_id: str = "", salary: str = "",
                   job_type: str = "Full-time", experience: str = "0-2 years",
                   ats_score: float = 0, matched_keywords: list = None,
                   missing_keywords: list = None, is_saved: int = 0,
                   source_url: str = "", apply_url: str = "") -> int:
        
        clean_url = (url or source_url or apply_url or "").strip()
        clean_source_url = (source_url or clean_url).strip()
        clean_apply_url = (apply_url or clean_url).strip()
        job_hash = self._generate_job_hash(company, title, clean_url)
        matched_json = json.dumps(matched_keywords or [])
        missing_json = json.dumps(missing_keywords or [])

        with self._connect() as conn:
            # UPSERT: single query instead of SELECT + INSERT/UPDATE
            conn.execute("""
                INSERT INTO jobs
                (title, company, location, description, requirements, url, source, source_job_id,
                 job_hash, salary, job_type, experience, ats_score, matched_keywords, missing_keywords, is_saved,
                 source_url, apply_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_hash) DO UPDATE SET
                    url=excluded.url,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    apply_url=excluded.apply_url,
                    location=excluded.location,
                    description=excluded.description,
                    requirements=excluded.requirements,
                    ats_score=excluded.ats_score,
                    matched_keywords=excluded.matched_keywords,
                    missing_keywords=excluded.missing_keywords,
                    updated_at=datetime('now')
            """, (title, company, location, description, requirements, clean_url, source, source_job_id,
                  job_hash, salary, job_type, experience, ats_score, matched_json, missing_json, is_saved,
                  clean_source_url, clean_apply_url))
            
            # Get the ID (works for both insert and update)
            row = conn.execute("SELECT id FROM jobs WHERE job_hash=?", (job_hash,)).fetchone()
            return row["id"] if row else 0

    def get_all_jobs(self, search: str = "", min_ats: float = 0) -> list[dict]:
        with self._connect() as conn:
            query = "SELECT * FROM jobs WHERE ats_score >= ?"
            params = [min_ats]
            if search:
                query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
                pattern = f"%{search}%"
                params.extend([pattern, pattern, pattern])
            query += " ORDER BY ats_score DESC, created_at DESC"

            rows = conn.execute(query, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                try:
                    d["matched_keywords"] = json.loads(d["matched_keywords"]) if d.get("matched_keywords") else []
                except Exception:
                    d["matched_keywords"] = []
                try:
                    d["missing_keywords"] = json.loads(d["missing_keywords"]) if d.get("missing_keywords") else []
                except Exception:
                    d["missing_keywords"] = []
                
                main_url = (d.get("source_url") or d.get("url") or d.get("apply_url") or "").strip()
                d["url"] = main_url
                d["source_url"] = d.get("source_url") or main_url
                d["apply_url"] = d.get("apply_url") or main_url
                d["job_url"] = main_url
                results.append(d)
            return results

    def get_job_by_id(self, job_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row:
                d = dict(row)
                try:
                    d["matched_keywords"] = json.loads(d["matched_keywords"]) if d.get("matched_keywords") else []
                except Exception:
                    d["matched_keywords"] = []
                try:
                    d["missing_keywords"] = json.loads(d["missing_keywords"]) if d.get("missing_keywords") else []
                except Exception:
                    d["missing_keywords"] = []
                
                main_url = (d.get("source_url") or d.get("url") or d.get("apply_url") or "").strip()
                d["url"] = main_url
                d["source_url"] = d.get("source_url") or main_url
                d["apply_url"] = d.get("apply_url") or main_url
                d["job_url"] = main_url
                return d
            return None

    def toggle_save_job(self, job_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT is_saved FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row:
                new_state = 0 if row["is_saved"] else 1
                conn.execute("UPDATE jobs SET is_saved=? WHERE id=?", (new_state, job_id))
                return bool(new_state)
            return False

    def update_job_ats(self, job_id: int, ats_score: float, matched: list = None, missing: list = None):
        matched_json = json.dumps(matched or [])
        missing_json = json.dumps(missing or [])
        with self._connect() as conn:
            conn.execute(
                """UPDATE jobs SET ats_score=?, matched_keywords=?, missing_keywords=?, updated_at=datetime('now')
                   WHERE id=?""",
                (ats_score, matched_json, missing_json, job_id)
            )

    def batch_update_ats(self, updates: list[dict]):
        """Batch update ATS scores for multiple jobs in a single transaction."""
        if not updates:
            return
        with self._connect() as conn:
            conn.executemany(
                """UPDATE jobs SET ats_score=?, matched_keywords=?, missing_keywords=?, updated_at=datetime('now')
                   WHERE id=?""",
                [(u["ats_score"], json.dumps(u.get("matched", [])), json.dumps(u.get("missing", [])), u["job_id"]) for u in updates]
            )

    def batch_insert_jobs(self, jobs: list[dict]) -> list[int]:
        """Insert or upsert multiple jobs in a single transaction. Returns list of job IDs."""
        if not jobs:
            return []
        ids = []
        with self._connect() as conn:
            for job in jobs:
                clean_url = (
                    job.get("source_url") or
                    job.get("sourceUrl") or
                    job.get("original_url") or
                    job.get("originalUrl") or
                    job.get("url") or
                    job.get("job_url") or
                    job.get("jobUrl") or
                    job.get("apply_url") or
                    job.get("applyUrl") or
                    ""
                ).strip()
                s_url = (job.get("source_url") or clean_url).strip()
                a_url = (job.get("apply_url") or clean_url).strip()

                job_hash = self._generate_job_hash(
                    job.get("company", ""), job.get("title", ""), clean_url
                )
                matched_json = json.dumps(job.get("matched_keywords", []))
                missing_json = json.dumps(job.get("missing_keywords", []))
                conn.execute("""
                    INSERT INTO jobs
                    (title, company, location, description, requirements, url, source, source_job_id,
                     job_hash, salary, job_type, experience, ats_score, matched_keywords, missing_keywords, is_saved,
                     source_url, apply_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(job_hash) DO UPDATE SET
                        url=excluded.url,
                        source=excluded.source,
                        source_url=excluded.source_url,
                        apply_url=excluded.apply_url,
                        location=excluded.location,
                        description=excluded.description,
                        requirements=excluded.requirements,
                        ats_score=excluded.ats_score,
                        matched_keywords=excluded.matched_keywords,
                        missing_keywords=excluded.missing_keywords,
                        updated_at=datetime('now')
                """, (
                    job.get("title", ""), job.get("company", ""), job.get("location", ""),
                    job.get("description", job.get("jd_text", "")), job.get("requirements", ""),
                    clean_url, job.get("source", "Live"), job.get("source_job_id", ""),
                    job_hash, job.get("salary", ""), job.get("job_type", "Full-time"),
                    job.get("experience", "0-2 years"), job.get("ats_score", 0),
                    matched_json, missing_json, job.get("is_saved", 0),
                    s_url, a_url
                ))
                row = conn.execute("SELECT id FROM jobs WHERE job_hash=?", (job_hash,)).fetchone()
                ids.append(row["id"] if row else 0)
        return ids

    def delete_job(self, job_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    # ─── Applications CRUD ────────────────────────────────────────────

    def create_application(self, job_id: int, status: str = "Saved", cover_letter: str = "",
                           resume_used: str = "", email: str = "", notes: str = "") -> int:
        valid_statuses = ["Saved", "Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]
        if status not in valid_statuses:
            status = "Saved"

        with self._connect() as conn:
            # Check if application already exists for this job
            row = conn.execute("SELECT id FROM applications WHERE job_id=?", (job_id,)).fetchone()
            if row:
                conn.execute(
                    """UPDATE applications SET status=?, cover_letter=?, resume_used=?, email=?, notes=?, updated_at=datetime('now')
                       WHERE id=?""",
                    (status, cover_letter, resume_used, email, notes, row["id"])
                )
                return row["id"]

            cur = conn.execute(
                """INSERT INTO applications (job_id, status, cover_letter, resume_used, email, notes)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (job_id, status, cover_letter, resume_used, email, notes)
            )
            return cur.lastrowid

    def update_application_status(self, app_id: int, status: str, notes: str = None):
        valid_statuses = ["Saved", "Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status {status}. Must be one of {valid_statuses}")
        with self._connect() as conn:
            if notes is not None:
                conn.execute(
                    "UPDATE applications SET status=?, notes=?, updated_at=datetime('now') WHERE id=?",
                    (status, notes, app_id)
                )
            else:
                conn.execute(
                    "UPDATE applications SET status=?, updated_at=datetime('now') WHERE id=?",
                    (status, app_id)
                )

    def mark_email_sent(self, app_id: int, email_recipient: str = ""):
        with self._connect() as conn:
            conn.execute(
                """UPDATE applications SET email_sent=1, status='Applied', email=?, updated_at=datetime('now')
                   WHERE id=?""",
                (email_recipient, app_id)
            )

    def get_all_applications(self) -> list[dict]:
        with self._connect() as conn:
            query = """
                SELECT a.*, j.title as job_title, j.company, j.location, j.ats_score, j.source, j.url, j.source_url, j.apply_url
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                ORDER BY a.updated_at DESC
            """
            rows = conn.execute(query).fetchall()
            res = []
            for r in rows:
                d = dict(r)
                main_url = (d.get("source_url") or d.get("url") or d.get("apply_url") or "").strip()
                d["url"] = main_url
                d["source_url"] = d.get("source_url") or main_url
                d["apply_url"] = d.get("apply_url") or main_url
                d["job_url"] = main_url
                res.append(d)
            return res

    def get_application_by_id(self, app_id: int) -> dict | None:
        with self._connect() as conn:
            query = """
                SELECT a.*, j.title as job_title, j.company, j.location, j.ats_score, j.source, j.url, j.source_url, j.apply_url
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                WHERE a.id = ?
            """
            row = conn.execute(query, (app_id,)).fetchone()
            if row:
                d = dict(row)
                main_url = (d.get("source_url") or d.get("url") or d.get("apply_url") or "").strip()
                d["url"] = main_url
                d["source_url"] = d.get("source_url") or main_url
                d["apply_url"] = d.get("apply_url") or main_url
                d["job_url"] = main_url
                return d
            return None

    def delete_application(self, app_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM applications WHERE id=?", (app_id,))

    # ─── Cover Letters CRUD ───────────────────────────────────────────

    def save_cover_letter(self, job_id: int, content: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO cover_letters (job_id, content) VALUES (?, ?)",
                (job_id, content)
            )
            # Also sync with application if exists
            conn.execute(
                "UPDATE applications SET cover_letter=? WHERE job_id=?",
                (content, job_id)
            )
            return cur.lastrowid

    def get_cover_letter(self, job_id: int) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM cover_letters WHERE job_id=? ORDER BY created_at DESC LIMIT 1",
                (job_id,)
            ).fetchone()
            return dict(row) if row else None

    # ─── Dashboard Stats (Consolidated: 9 queries → 2) ───────────────

    def get_stats(self) -> dict:
        with self._connect() as conn:
            # Consolidated job stats (1 query instead of 3)
            job_row = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_saved=1 THEN 1 ELSE 0 END) as saved,
                       AVG(CASE WHEN ats_score > 0 THEN ats_score END) as avg_ats
                FROM jobs
            """).fetchone()

            # Consolidated application stats
            app_row = conn.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status='Saved' THEN 1 ELSE 0 END) as saved,
                       SUM(CASE WHEN status='Applied' THEN 1 ELSE 0 END) as applied,
                       SUM(CASE WHEN status='Screening' THEN 1 ELSE 0 END) as screening,
                       SUM(CASE WHEN email_sent=1 THEN 1 ELSE 0 END) as emails,
                       SUM(CASE WHEN status='Interview' THEN 1 ELSE 0 END) as interviews,
                       SUM(CASE WHEN status='Offer' THEN 1 ELSE 0 END) as offers,
                       SUM(CASE WHEN status='Rejected' THEN 1 ELSE 0 END) as rejected,
                       SUM(CASE WHEN status='Withdrawn' THEN 1 ELSE 0 END) as withdrawn
                FROM applications
            """).fetchone()

            return {
                "total_jobs":     job_row["total"] or 0,
                "saved_jobs":     job_row["saved"] or 0,
                "total_apps":     app_row["total"] or 0,
                "saved_apps":     app_row["saved"] or 0,
                "applied_apps":   app_row["applied"] or 0,
                "screening_apps": app_row["screening"] or 0,
                "emails_sent":    app_row["emails"] or 0,
                "interviews":     app_row["interviews"] or 0,
                "offers":         app_row["offers"] or 0,
                "rejected":       app_row["rejected"] or 0,
                "withdrawn":      app_row["withdrawn"] or 0,
                "avg_ats":        round(job_row["avg_ats"] or 0, 1),
            }

    def get_ats_details(self) -> dict:
        """Fetch detailed ATS score metrics, job breakdowns, keyword frequencies, and score distributions."""
        all_jobs = self.get_all_jobs()
        scored_jobs = [j for j in all_jobs if j.get("ats_score", 0) > 0]
        
        avg_ats = round(sum(j["ats_score"] for j in scored_jobs) / len(scored_jobs), 1) if scored_jobs else 0.0
        
        # Distribution buckets
        distribution = {
            "90_100": len([j for j in scored_jobs if j["ats_score"] >= 90]),
            "80_89":  len([j for j in scored_jobs if 80 <= j["ats_score"] < 90]),
            "70_79":  len([j for j in scored_jobs if 70 <= j["ats_score"] < 80]),
            "60_69":  len([j for j in scored_jobs if 60 <= j["ats_score"] < 70]),
            "below_60": len([j for j in scored_jobs if j["ats_score"] < 60]),
        }
        
        # Keyword frequencies across scored jobs
        matched_freq = {}
        missing_freq = {}
        
        for j in scored_jobs:
            for kw in j.get("matched_keywords", []):
                if isinstance(kw, str) and kw.strip():
                    matched_freq[kw.strip()] = matched_freq.get(kw.strip(), 0) + 1
            for kw in j.get("missing_keywords", []):
                if isinstance(kw, str) and kw.strip():
                    missing_freq[kw.strip()] = missing_freq.get(kw.strip(), 0) + 1
                    
        top_matched = sorted([{"keyword": k, "count": v} for k, v in matched_freq.items()], key=lambda x: x["count"], reverse=True)[:10]
        top_missing = sorted([{"keyword": k, "count": v} for k, v in missing_freq.items()], key=lambda x: x["count"], reverse=True)[:10]
        
        return {
            "average_ats": avg_ats,
            "total_scored_jobs": len(scored_jobs),
            "total_jobs": len(all_jobs),
            "distribution": distribution,
            "scored_jobs": scored_jobs,
            "top_matched_keywords": top_matched,
            "top_missing_keywords": top_missing,
        }

    def get_conversion_details(self) -> dict:
        """Fetch detailed conversion metrics and stage breakdown analytics."""
        stats = self.get_stats()
        total_jobs = stats["total_jobs"]
        applied = stats["applied_apps"]
        interviews = stats["interviews"]
        offers = stats["offers"]
        total_apps = stats["total_apps"]
        
        interview_rate = round((interviews / applied * 100), 1) if applied > 0 else 0.0
        offer_rate = round((offers / applied * 100), 1) if applied > 0 else 0.0
        interview_to_offer_rate = round((offers / interviews * 100), 1) if interviews > 0 else 0.0
        overall_funnel_rate = round((offers / total_jobs * 100), 1) if total_jobs > 0 else 0.0
        discovered_to_applied_rate = round((applied / total_jobs * 100), 1) if total_jobs > 0 else 0.0
        
        recent_apps = self.get_all_applications()
        
        return {
            "stats": stats,
            "conversion_rates": {
                "interview_rate": interview_rate,
                "offer_rate": offer_rate,
                "interview_to_offer_rate": interview_to_offer_rate,
                "overall_funnel_rate": overall_funnel_rate,
                "discovered_to_applied_rate": discovered_to_applied_rate,
            },
            "recent_applications": recent_apps,
        }

    # ─── Agent Logs ───────────────────────────────────────────────────

    def log_agent_activity(self, agent_name: str, action: str, status: str = "Completed", details: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO agent_logs (agent_name, action, status, details) VALUES (?, ?, ?, ?)",
                (agent_name, action, status, details)
            )
            return cur.lastrowid

    def get_agent_logs(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
