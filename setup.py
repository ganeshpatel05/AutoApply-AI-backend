"""
AutoApply AI — One-Click Setup Script
Run this first: python setup.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def print_banner():
    banner = """
============================================================
              AutoApply AI — Setup Wizard
      MCA Minor Project | Decoupled Multi-Agent Architecture
============================================================
"""
    print(banner)


def check_python_version():
    print("[CHECK] Checking Python version...")
    if sys.version_info < (3, 10):
        print("[ERROR] Python 3.10+ is required. Please upgrade Python.")
        sys.exit(1)
    print(f"[OK] Python {sys.version_info.major}.{sys.version_info.minor} found")


def install_requirements():
    print("\n[DEPENDENCIES] Installing required packages...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            check=True
        )
        print("[OK] All packages installed successfully")
    except subprocess.CalledProcessError:
        print("[WARNING] Failed to install packages via setup script. You can run 'pip install -r requirements.txt' manually.")


def setup_env_file():
    print("\n[CONFIG] Setting up environment configuration...")
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    example_path = Path(".env.example")

    if not env_path.exists() and example_path.exists():
        shutil.copy(example_path, env_path)
        print("[OK] Created .env from .env.example")
    elif env_path.exists():
        print("[OK] .env file already exists")
    else:
        with open(env_path, "w") as f:
            f.write("OLLAMA_MODEL=mistral\nOLLAMA_BASE_URL=http://localhost:11434\n")
        print("[OK] Created default .env file")


def create_directories():
    print("\n[DIRECTORIES] Creating project directories...")
    dirs = [
        "database",
        "uploads/resumes",
        "uploads/cover_letters",
        "logs",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("[OK] Project directories created")


def init_database():
    print("\n[DATABASE] Initializing SQLite database...")
    try:
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db.init_db()
        print("[OK] Database initialized at database/autoapply.db")
    except Exception as e:
        print(f"[WARNING] Database init warning: {e}")


def check_ollama():
    print("\n[OLLAMA] Checking Ollama installation...")
    if shutil.which("ollama"):
        print("[OK] Ollama binary is installed in system PATH")
        print("     To download the recommended model: ollama pull mistral")
        print("     Then start local server: ollama serve")
    else:
        print("[INFO] Ollama not found in PATH.")
        print("       (AI Cover Letter feature will automatically fallback to intelligent template generation)")


def print_success():
    msg = """
============================================================
   Setup Complete! Here is how to run AutoApply AI:

   1. Start Ollama (Optional):  ollama serve
   2. Launch Backend API:      python api/main.py
   3. Launch UI Dashboard:      cd ../frontend && npm run dev
   4. Run CLI Pipeline:         python main.py --help
============================================================
"""
    print(msg)


if __name__ == "__main__":
    print_banner()
    check_python_version()
    install_requirements()
    setup_env_file()
    create_directories()
    init_database()
    check_ollama()
    print_success()
