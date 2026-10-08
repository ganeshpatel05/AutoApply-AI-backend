"""AutoApply AI — Utility Helper Functions"""

import re
import json
from datetime import datetime


def clean_text(text: str) -> str:
    """Remove excessive whitespace and special characters from text."""
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s\.\,\!\?\:\;\-\(\)\[\]\@\#]', '', text)
    return text.strip()


def extract_emails(text: str) -> list[str]:
    """Extract all email addresses from a block of text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return re.findall(pattern, text)


def extract_phone_numbers(text: str) -> list[str]:
    """Extract phone numbers from text."""
    pattern = r'[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{3,4}[-\s\.]?[0-9]{4,6}'
    return re.findall(pattern, text)


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)


def truncate_text(text: str, max_chars: int = 300, suffix: str = "...") -> str:
    """Truncate text to a maximum character count."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - len(suffix)] + suffix


def format_date(date_str: str) -> str:
    """Format a SQLite datetime string to human-readable format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return date_str


def ats_badge_color(score: float) -> str:
    """Return color hex based on ATS score."""
    if score >= 70:
        return "#22c55e"   # Green
    elif score >= 50:
        return "#f59e0b"   # Amber
    else:
        return "#ef4444"   # Red


def ats_badge_emoji(score: float) -> str:
    """Return emoji based on ATS score."""
    if score >= 70:
        return "🟢"
    elif score >= 50:
        return "🟡"
    else:
        return "🔴"


def status_color(status: str) -> str:
    """Return color for application status."""
    colors = {
        "Saved":     "#6366f1",
        "Applied":   "#3b82f6",
        "Interview": "#f59e0b",
        "Offer":     "#22c55e",
        "Rejected":  "#ef4444",
        "Withdrawn": "#6b7280",
    }
    return colors.get(status, "#6b7280")


def status_emoji(status: str) -> str:
    """Return emoji for application status."""
    emojis = {
        "Saved":     "⏳",
        "Applied":   "📧",
        "Interview": "🎤",
        "Offer":     "🎉",
        "Rejected":  "❌",
        "Withdrawn": "🛑",
    }
    return emojis.get(status, "❓")


def common_tech_keywords() -> list[str]:
    """Return a large list of common tech/job keywords for ATS scoring."""
    return [
        # Programming languages
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "kotlin", "swift", "r", "scala", "php", "ruby", "dart", "sql",
        # Web frameworks
        "react", "angular", "vue", "nextjs", "django", "flask", "fastapi",
        "spring", "nodejs", "express", "laravel", "rails",
        # Data / ML
        "machine learning", "deep learning", "nlp", "computer vision",
        "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
        "data science", "data analysis", "tableau", "power bi", "excel",
        # Cloud / DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
        "ci/cd", "jenkins", "github actions", "linux", "bash",
        # Databases
        "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
        "elasticsearch", "cassandra", "dynamodb",
        # Soft skills
        "communication", "teamwork", "leadership", "problem solving",
        "agile", "scrum", "project management", "analytical",
        # General
        "api", "rest", "graphql", "microservices", "git", "testing",
        "unit testing", "debugging", "documentation", "oop",
    ]
