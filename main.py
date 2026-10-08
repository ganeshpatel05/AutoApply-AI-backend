"""AutoApply AI — CLI Entry Point
Run the full pipeline from the command line.
Usage: python main.py --resume path/to/resume.pdf --role "Python Developer" --location "Bangalore"
"""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def print_banner():
    console.print(Panel.fit(
        "[bold cyan]AutoApply AI[/bold cyan]\n"
        "[dim]Multi-Agent Job Application Automation System[/dim]\n"
        "[dim]MCA Minor Project | Python + FastAPI + React Vite + Ollama + SQLite[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))


def print_jobs_table(jobs: list):
    table = Table(
        title="[JOBS] Scraped & Ranked Job Listings",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Rank", style="bold yellow", width=5)
    table.add_column("Title", style="bold white", width=30)
    table.add_column("Company", style="cyan", width=22)
    table.add_column("Location", style="green", width=14)
    table.add_column("ATS Score", style="bold", width=10)
    table.add_column("Source", style="dim", width=12)

    for i, job in enumerate(jobs, 1):
        score = job.get("ats_score", 0)
        score_style = (
            "[green]" if score >= 70 else
            "[yellow]" if score >= 50 else
            "[red]"
        )
        table.add_row(
            str(i),
            job.get("title", "")[:28],
            job.get("company", "")[:20],
            job.get("location", "")[:12],
            f"{score_style}{score:.1f}%[/]",
            job.get("source", ""),
        )

    console.print(table)



def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoApply AI — Automated Job Application Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --resume resume.pdf --role "Python Developer" --location "Bangalore"
  python main.py --resume resume.pdf --role "Data Scientist" --demo
  python main.py --init-db
  python main.py --stats
  python main.py --list-jobs
  python main.py --list-apps
        """
    )
    parser.add_argument("--resume", type=str, help="Path to your resume PDF file")
    parser.add_argument("--role", type=str, default="Software Developer", help="Target job role")
    parser.add_argument("--location", type=str, default="", help="Preferred job location")
    parser.add_argument("--experience", type=str, default="0", help="Years of experience")
    parser.add_argument("--demo", action="store_true", help="Use bundled demo jobs")
    parser.add_argument("--init-db", action="store_true", help="Initialize/reset the database")
    parser.add_argument("--stats", action="store_true", help="Show application statistics")
    parser.add_argument("--list-jobs", action="store_true", help="List all jobs in database")
    parser.add_argument("--list-apps", action="store_true", help="List all applications in database")
    return parser.parse_args()


def init_database():
    from database.db_manager import DatabaseManager
    console.print("[cyan]Initializing database...[/cyan]")
    db = DatabaseManager()
    db.init_db()
    console.print("[green]OK: Database initialized at database/autoapply.db[/green]")


def show_stats():
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    try:
        stats = db.get_stats()
        console.print(Panel(
            f"[bold]AutoApply AI Database Statistics[/bold]\n\n"
            f"  Total Jobs Found : [cyan]{stats['total_jobs']}[/cyan]\n"
            f"  Saved Jobs       : [cyan]{stats['saved_jobs']}[/cyan]\n"
            f"  Total Apps       : [cyan]{stats['total_apps']}[/cyan]\n"
            f"  Applied Status   : [blue]{stats['applied_apps']}[/blue]\n"
            f"  Emails Sent      : [green]{stats['emails_sent']}[/green]\n"
            f"  Interviews       : [yellow]{stats['interviews']}[/yellow]\n"
            f"  Offers           : [bold green]{stats['offers']}[/bold green]\n"
            f"  Average ATS Score: [magenta]{stats['avg_ats']}%[/magenta]",
            border_style="cyan",
        ))
    except Exception as e:
        console.print(f"[red]Error fetching stats: {e}[/red]")


def list_jobs():
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    jobs = db.get_all_jobs()
    if not jobs:
        console.print("[yellow]No jobs found in database. Run with --resume to search.[/yellow]")
        return
    print_jobs_table(jobs)


def list_apps():
    from database.db_manager import DatabaseManager
    db = DatabaseManager()
    apps = db.get_all_applications()
    if not apps:
        console.print("[yellow]No applications found in database.[/yellow]")
        return

    table = Table(
        title="[APPS] Applications Tracker",
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("ID", width=5)
    table.add_column("Job Title", width=28)
    table.add_column("Company", width=22)
    table.add_column("ATS %", width=8)
    table.add_column("Status", width=12)
    table.add_column("Email", width=8)
    table.add_column("Date", width=16)

    status_colors = {
        "Saved": "cyan",
        "Applied": "blue",
        "Interview": "yellow",
        "Offer": "bold green",
        "Rejected": "red",
        "Withdrawn": "dim",
    }
    for app in apps:
        color = status_colors.get(app["status"], "white")
        table.add_row(
            str(app["id"]),
            app.get("job_title", "")[:26],
            app.get("company", "")[:20],
            f"{app.get('ats_score', 0):.1f}%",
            f"[{color}]{app['status']}[/{color}]",
            "YES" if app.get("email_sent") else "NO",
            str(app.get("applied_at", ""))[:16],
        )
    console.print(table)



def run_pipeline_cli(args):
    from agents.orchestrator import AutoApplyOrchestrator

    resume_path = None
    if args.resume:
        p = Path(args.resume)
        if not p.exists():
            console.print(f"[red]ERROR: Resume file not found: {p}[/red]")
            sys.exit(1)
        resume_path = str(p)

    print_banner()
    console.print(f"\n[bold]Pipeline Configuration:[/bold]")
    console.print(f"   Resume     : {resume_path or 'Using Active DB Resume'}")
    console.print(f"   Target Role: {args.role}")
    console.print(f"   Location   : {args.location or 'All India'}")
    console.print(f"   Experience : {args.experience} years")
    console.print(f"   Demo Mode  : {'ON' if args.demo else 'OFF'}\n")

    orchestrator = AutoApplyOrchestrator()

    console.print("[cyan]Running Multi-Agent Orchestrator...[/cyan]")
    results = orchestrator.run_pipeline(
        resume_pdf_path=resume_path,
        role=args.role,
        location=args.location,
        experience=args.experience,
        demo_mode=args.demo,
        generate_cover_letters_count=3
    )
    console.print("[green]Multi-Agent Pipeline Completed![/green]")


    if results.get("errors"):
        for err in results["errors"]:
            console.print(f"[yellow]Warning: {err}[/yellow]")

    if results.get("ranked_jobs"):
        print_jobs_table(results["ranked_jobs"])

    console.print(Panel(
        f"[bold green]Execution Finished![/bold green]\n\n"
        f"  Candidate      : [cyan]{results['resume'].get('name', 'Candidate') if results.get('resume') else 'N/A'}[/cyan]\n"
        f"  Jobs Discovered: [cyan]{len(results['jobs'])}[/cyan]\n"
        f"  Cover Letters  : [cyan]{len(results['cover_letters'])}[/cyan]\n"
        f"  Applications   : [cyan]{len(results['applications'])}[/cyan]\n\n"
        f"[dim]Launch UI: [bold]cd ../frontend && npm run dev[/bold][/dim]\n"
        f"[dim]Launch Backend: [bold]python api/main.py[/bold][/dim]",
        border_style="green",
        padding=(1, 3),
    ))



def main():
    args = parse_args()

    if args.init_db:
        init_database()
        return

    if args.stats:
        show_stats()
        return

    if args.list_jobs:
        list_jobs()
        return

    if args.list_apps:
        list_apps()
        return

    if not args.resume:
        # Check if an active resume exists in DB
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        active = db.get_active_resume()
        if not active:
            console.print("[yellow]No resume file provided and no active resume in DB.[/yellow]")
            console.print("[dim]Usage: python main.py --resume resume.pdf --role 'Python Developer'[/dim]")
            console.print("[dim]Run python main.py --help for all options[/dim]")
            return

    run_pipeline_cli(args)


if __name__ == "__main__":
    main()
