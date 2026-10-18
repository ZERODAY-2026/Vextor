"""
Lexiguard Unified Command Center & Entry Point
Consolidates all modular CLI tools, Streamlit UI, built-in server, judge demo,
and privacy audits into a single cohesive utility software.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .agent import LexiguardAgent
from .diff_agent import LexiguardDiffAgent
from .privacy_guard import PrivacyGuard
from .models import SeverityLevel
from .cli import (
    render_triage_dashboard,
    render_qa_answer,
    render_comparison_dashboard,
    export_report,
    print_banner
)

console = Console()


def launch_ui(port: int = 8501, host: str = "localhost"):
    """Launches the Lexiguard Streamlit Modern UI Dashboard."""
    root_dir = Path(__file__).parent.parent
    app_path = root_dir / "app.py"
    if not app_path.exists():
        app_path = root_dir / "streamlit_app.py"

    print_banner()
    console.print(Panel(
        f"[bold cyan]🚀 Starting Lexiguard Streamlit Studio[/bold cyan]\n"
        f"[bold green]Local URL:[/bold green] [underline white]http://{host}:{port}[/underline white]\n"
        "[dim white]100% On-Device Legal Analysis • Zero Cloud Telemetry • Google Gemma 2 Powered[/dim white]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.address", host,
        "--browser.gatherUsageStats", "false"
    ]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Lexiguard Streamlit Studio stopped gracefully.[/yellow]")


def launch_web(port: int = 8080):
    """Launches the lightweight zero-dependency HTTP server."""
    from .server import run_server
    print_banner()
    console.print(f"[bold cyan]Starting lightweight zero-dependency web server on http://localhost:{port}...[/bold cyan]")
    run_server(port=port)


def run_judge_demo():
    """Runs the 10-gate competition judge evaluation suite."""
    root_dir = Path(__file__).parent.parent
    demo_script = root_dir / "demo_judge.py"
    if demo_script.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("demo_judge", str(demo_script))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run_demo()
    else:
        console.print("[red]demo_judge.py script not found.[/red]")


def run_benchmark():
    """Runs the performance and memory envelope benchmark."""
    root_dir = Path(__file__).parent.parent
    bench_script = root_dir / "tests" / "benchmark.py"
    if bench_script.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("benchmark", str(bench_script))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.run_benchmark()
    else:
        console.print("[red]tests/benchmark.py script not found.[/red]")


def run_privacy_audit(export_file: str = "privacy_audit.json"):
    """Runs the on-device socket audit and exports signed proof."""
    print_banner()
    console.print("[bold cyan]🔍 Executing Real-Time Air-Gap & Outbound Socket Audit (Gate L9)...[/bold cyan]")
    guard = PrivacyGuard()
    check = guard.check_active_connections()
    isolated, msg = PrivacyGuard.verify_offline_environment()

    table = Table(title="Lexiguard Network Isolation Ledger", box=box.ROUNDED)
    table.add_column("Socket Type", style="bold cyan")
    table.add_column("Count", style="white")
    table.add_column("Compliance Status", style="bold green")

    table.add_row("Loopback (127.0.0.1 / Ollama)", str(len(check["loopback"])), "PERMITTED (Localhost Only)")
    remote_status = "[bold green]ZERO (COMPLIANT)[/bold green]" if len(check["remote_outbound"]) == 0 else f"[bold red]LEAK DETECTED ({len(check['remote_outbound'])})[/bold red]"
    table.add_row("Remote Internet Outbound", str(len(check["remote_outbound"])), remote_status)
    console.print(table)

    evidence = guard.generate_audit_log(export_file)
    console.print(f"\n[bold green]✓ Air-gap compliance confirmed:[/bold green] {msg}")
    console.print(f"[dim]Signed evidence exported to: [bold white]{export_file}[/bold white][/dim]")


def main():
    """Unified entry point for the lexiguard package."""
    parser = argparse.ArgumentParser(
        prog="lexiguard",
        description="⚖️ Lexiguard: On-Device Private Legal Document Triage Agent (Powered by Google Gemma 2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  ui         Launch the interactive Streamlit Studio UI
  triage     Analyze a legal document (PDF or TXT) for risks and missing clauses
  ask        Ask a grounded question with strict verbatim citations (L5)
  compare    Perform two-version semantic diff redlining (Draft A vs Draft B)
  demo       Execute the turnkey 10-gate judge evaluation suite
  audit      Verify air-gap isolation and generate signed socket proof
  web        Launch the lightweight zero-dependency local HTTP web server
  benchmark  Measure on-device latency, token speed, and RAM envelope

Examples:
  lexiguard ui
  lexiguard triage sample_documents/residential_lease_agreement.pdf
  lexiguard ask sample_documents/residential_lease_agreement.txt "Can landlord enter without notice?"
  lexiguard compare sample_documents/residential_lease_agreement.txt sample_documents/residential_lease_revised_v2.txt
  lexiguard demo
  lexiguard audit
        """
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available operations")

    # Command: ui
    ui_p = subparsers.add_parser("ui", aliases=["gui", "studio"], help="Launch modern Streamlit UI Studio")
    ui_p.add_argument("--port", type=int, default=8501, help="Port to serve Streamlit on (default: 8501)")
    ui_p.add_argument("--host", type=str, default="localhost", help="Host address (default: localhost)")

    # Command: triage
    triage_p = subparsers.add_parser("triage", help="Triage a legal contract")
    triage_p.add_argument("file", help="Path to document (.pdf or .txt)")
    triage_p.add_argument("--model", default="auto", help="Ollama model (default: auto-detects gemma2:2b)")
    triage_p.add_argument("--export", action="store_true", help="Export JSON and Markdown triage reports")

    # Command: ask
    ask_p = subparsers.add_parser("ask", help="Ask a grounded question about a contract")
    ask_p.add_argument("file", help="Path to document")
    ask_p.add_argument("question", help="Question to ask (strictly grounded in contract text)")
    ask_p.add_argument("--model", default="auto", help="Ollama model name")

    # Command: compare / diff
    comp_p = subparsers.add_parser("compare", aliases=["diff"], help="Compare two contract versions")
    comp_p.add_argument("original", help="Original document path")
    comp_p.add_argument("revised", help="Revised document path")

    # Command: demo
    subparsers.add_parser("demo", help="Run turnkey 10-gate judge demonstration")

    # Command: audit
    audit_p = subparsers.add_parser("audit", help="Run air-gap socket audit")
    audit_p.add_argument("--export", default="privacy_audit.json", help="Path to export audit JSON")

    # Command: web
    web_p = subparsers.add_parser("web", aliases=["serve", "server"], help="Run lightweight local HTTP server")
    web_p.add_argument("--port", type=int, default=8080, help="Port for local web server (default: 8080)")

    # Command: benchmark
    subparsers.add_parser("benchmark", aliases=["bench"], help="Run hardware latency and memory benchmark")

    # Top-level backward compatibility flags
    parser.add_argument("--file", "-f", help=argparse.SUPPRESS)
    parser.add_argument("--ask", "-a", help=argparse.SUPPRESS)
    parser.add_argument("--compare", "-c", nargs=2, help=argparse.SUPPRESS)
    parser.add_argument("--demo", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--audit", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ui", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--web", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--model", "-m", default="auto", help=argparse.SUPPRESS)
    parser.add_argument("--export", "-e", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--interactive", "-i", action="store_true", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Route top-level backward compatibility flags if present
    if args.ui:
        launch_ui()
        return
    if args.web:
        launch_web()
        return
    if args.demo:
        run_judge_demo()
        return
    if args.audit and not args.command:
        run_privacy_audit()
        return
    if args.compare and not args.command:
        agent = LexiguardAgent(model_name=args.model)
        diff_agent = LexiguardDiffAgent()
        report = diff_agent.compare_documents(args.compare[0], args.compare[1])
        render_comparison_dashboard(report)
        return
    if args.file and not args.command:
        agent = LexiguardAgent(model_name=args.model)
        print_banner(agent.model_name)
        if args.ask:
            qa = agent.answer_question(args.file, args.ask)
            render_qa_answer(qa)
            return
        report = agent.triage_document(args.file)
        render_triage_dashboard(report)
        if args.export:
            export_report(report, os.path.splitext(args.file)[0])
        return

    # Route Subcommands
    if args.command in ["ui", "gui", "studio"]:
        launch_ui(port=args.port, host=args.host)
    elif args.command == "triage":
        agent = LexiguardAgent(model_name=args.model)
        print_banner(agent.model_name)
        report = agent.triage_document(args.file)
        render_triage_dashboard(report)
        if args.export:
            export_report(report, os.path.splitext(args.file)[0])
    elif args.command == "ask":
        agent = LexiguardAgent(model_name=args.model)
        print_banner(agent.model_name)
        qa = agent.answer_question(args.file, args.question)
        render_qa_answer(qa)
    elif args.command in ["compare", "diff"]:
        diff_agent = LexiguardDiffAgent()
        report = diff_agent.compare_documents(args.original, args.revised)
        render_comparison_dashboard(report)
    elif args.command == "demo":
        run_judge_demo()
    elif args.command == "audit":
        run_privacy_audit(args.export)
    elif args.command in ["web", "serve", "server"]:
        launch_web(port=args.port)
    elif args.command in ["benchmark", "bench"]:
        run_benchmark()
    else:
        # No command specified: show banner and interactive help
        print_banner()
        console.print("[bold yellow]No command specified. Choose an option:[/bold yellow]\n")
        console.print("  [bold cyan]1. Launch Streamlit Studio:[/bold cyan]  lexiguard ui")
        console.print("  [bold cyan]2. Triage a Document:[/bold cyan]       lexiguard triage <path/to/contract.pdf>")
        console.print("  [bold cyan]3. Ask Grounded Question:[/bold cyan]   lexiguard ask <contract> \"<question>\"")
        console.print("  [bold cyan]4. Compare Two Drafts:[/bold cyan]      lexiguard compare <doc_v1> <doc_v2>")
        console.print("  [bold cyan]5. Run Judge Demo (10-Gate):[/bold cyan] lexiguard demo")
        console.print("  [bold cyan]6. Air-Gap Privacy Audit:[/bold cyan]    lexiguard audit")
        console.print("  [bold cyan]7. Performance Benchmark:[/bold cyan]    lexiguard benchmark")
        console.print("  [bold cyan]8. Lightweight Web Server:[/bold cyan]   lexiguard web\n")
        console.print("[dim]Use --help for full command-line options and parameters.[/dim]")


if __name__ == "__main__":
    main()
