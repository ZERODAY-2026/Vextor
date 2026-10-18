"""
Lexiguard Terminal User Interface
Built with Rich for high-clarity color-coded triage visualization, accessibility,
and interactive clause inspection.
"""

import sys
import os
import argparse
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from .agent import LexiguardAgent
from .models import SeverityLevel, DocumentTriageReport
from .privacy_guard import PrivacyGuard


console = Console()


def print_banner():
    """Prints Lexiguard security and identity banner."""
    banner = Text()
    banner.append("⚖️  LEXIGUARD ", style="bold cyan")
    banner.append("| Private Legal Document Triage Agent\n", style="bold white")
    banner.append("🔒 100% On-Device Local Processing (Google Gemma Edge) | Zero Cloud Telemetry\n", style="italic green")
    banner.append("⚠️  Notice: Educational document comprehension tool. Not legal advice.", style="dim yellow")
    console.print(Panel(banner, border_style="cyan", box=box.ROUNDED))


def render_triage_dashboard(report: DocumentTriageReport):
    """Renders the comprehensive triage results using color-coded tables and panels."""
    # 1. Document Overview Panel
    meta_table = Table(show_header=False, box=box.SIMPLE)
    meta_table.add_column("Field", style="bold cyan", width=22)
    meta_table.add_column("Value", style="white")

    risk_style = "bold red" if report.overall_risk_rating == SeverityLevel.HIGH_RISK else \
                 "bold yellow" if report.overall_risk_rating == SeverityLevel.CAUTION_AMBER else "bold green"

    meta_table.add_row("Document Name", report.metadata.filename)
    meta_table.add_row("Document Category", report.metadata.detected_document_type)
    meta_table.add_row("Identified Parties", ", ".join(report.metadata.identified_parties) or "Unspecified")
    meta_table.add_row("Term / Effective Dates", report.metadata.effective_dates_or_term or "Unspecified")
    meta_table.add_row("Governing Jurisdiction", report.metadata.governing_jurisdiction_stated or "Not specified")
    meta_table.add_row("Overall Risk Level", Text(report.overall_risk_rating.value, style=risk_style))

    console.print(Panel(meta_table, title="[bold]Document Overview & Parties[/bold]", border_style="blue", box=box.ROUNDED))

    # 2. Executive Summary
    console.print(Panel(
        Text(report.executive_summary, style="white"),
        title="[bold]Plain-Language Executive Triage[/bold]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 3. Adversarial / Prompt Injection Warnings (if any)
    if report.adversarial_warnings:
        warn_text = Text()
        for w in report.adversarial_warnings:
            warn_text.append(f"⚠️ {w}\n", style="bold red")
        console.print(Panel(warn_text, title="[bold red]Adversarial Text & Anomaly Warnings[/bold red]", border_style="red", box=box.HEAVY))

    # 4. Clauses Table
    clause_table = Table(title="Key Clauses & Risk Breakdown (L3 - L7)", box=box.ROUNDED)
    clause_table.add_column("ID", style="bold cyan", width=9)
    clause_table.add_column("Category", style="magenta", width=18)
    clause_table.add_column("Severity", justify="center", width=14)
    clause_table.add_column("Plain-Language Summary", style="white", width=42)
    clause_table.add_column("Identifiable Passage (Citation)", style="dim italic", width=34)

    for c in report.clauses:
        sev_color = "red" if c.severity == SeverityLevel.HIGH_RISK else \
                    "yellow" if c.severity == SeverityLevel.CAUTION_AMBER else \
                    "green" if c.severity == SeverityLevel.STANDARD_LOW else "blue"
        
        badge = f"[{sev_color}]{c.severity.value}[/{sev_color}]"
        citation_text = f"\"{c.citation.verbatim_quote[:60]}...\" ({c.citation.section_reference or 'P. ' + str(c.citation.page_number)})"

        clause_table.add_row(
            c.clause_id,
            c.category,
            badge,
            c.plain_language_summary,
            citation_text
        )

    console.print(clause_table)

    # 5. Silent Clauses (What the document is missing)
    if report.silent_clauses:
        silent_table = Table(title="Audit of Silent & Missing Clauses (Key Protection Omissions)", box=box.ROUNDED)
        silent_table.add_column("Protection Topic", style="bold yellow", width=30)
        silent_table.add_column("Risk Implication of Silence", style="white", width=46)
        silent_table.add_column("Suggested Inquiry / Action", style="cyan", width=38)

        for s in report.silent_clauses:
            silent_table.add_row(
                f"❌ {s.topic}",
                s.risk_implication,
                s.suggested_inquiry
            )
        console.print(silent_table)

    # 6. Safe Escalation to Counsel (L8)
    if report.escalations:
        esc_table = Table(title="Safe Escalation Checklist (Questions for a Legal Professional)", box=box.ROUNDED)
        esc_table.add_column("Trigger Clause", style="bold magenta", width=22)
        esc_table.add_column("Recommended Specialist", style="green", width=26)
        esc_table.add_column("Key Questions to Ask Counsel", style="white", width=65)

        for esc in report.escalations:
            questions = "\n• " + "\n• ".join(esc.specific_questions_for_counsel)
            esc_table.add_row(
                esc.trigger_clause,
                esc.recommended_specialist,
                questions
            )
        console.print(esc_table)

    # 7. Privacy Proof & Mandatory Disclaimer
    privacy_text = (
        f"✓ Audit Result: {report.privacy_audit.get('compliance_status', 'PASSED')}\n"
        f"✓ Mode: {report.privacy_audit.get('mode', '100% On-Device')}\n"
        f"✓ Outbound Network Calls: {report.privacy_audit.get('remote_network_requests', 0)}\n"
        f"✓ Verification Timestamp: {report.privacy_audit.get('audit_timestamp', 'Local')}"
    )
    console.print(Panel(Text(privacy_text, style="bold green"), title="[bold]Privacy & Network Isolation Proof (L9)[/bold]", border_style="green", box=box.ROUNDED))

    console.print(Panel(
        Text(report.legal_disclaimer, style="italic yellow"),
        title="[bold yellow]Non-Legal-Advice Compliance Notice (L8)[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED
    ))


def export_report(report: DocumentTriageReport, base_filename: str):
    """Exports triage results to JSON and Markdown."""
    json_path = f"{base_filename}_triage.json"
    md_path = f"{base_filename}_triage.md"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    # Save Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Lexiguard Legal Triage Report: {report.metadata.filename}\n\n")
        f.write(f"**Overall Risk Rating**: {report.overall_risk_rating.value}\n")
        f.write(f"**Category**: {report.metadata.detected_document_type}\n\n")
        f.write(f"## Executive Summary\n{report.executive_summary}\n\n")
        f.write("## Analyzed Clauses\n")
        for c in report.clauses:
            f.write(f"### {c.clause_id}: {c.category} [{c.severity.value}]\n")
            f.write(f"- **Plain Language**: {c.plain_language_summary}\n")
            f.write(f"- **Explicit Statement**: {c.explicit_statement}\n")
            f.write(f"- **Potential Interpretation**: {c.potential_interpretation}\n")
            f.write(f"- **Practical Concern**: {c.practical_concern}\n")
            f.write(f"- **Identifiable Passage**: *\"{c.citation.verbatim_quote}\"* ({c.citation.section_reference})\n\n")

        if report.silent_clauses:
            f.write("## Silent / Missing Protections\n")
            for s in report.silent_clauses:
                f.write(f"- **{s.topic}**: {s.risk_implication}\n")
                f.write(f"  *Suggested Inquiry*: {s.suggested_inquiry}\n\n")

        if report.escalations:
            f.write("## Escalation to Legal Professional\n")
            for e in report.escalations:
                f.write(f"### {e.trigger_clause} (Consult: {e.recommended_specialist})\n")
                for q in e.specific_questions_for_counsel:
                    f.write(f"- {q}\n")
                f.write("\n")

        f.write(f"---\n\n> {report.legal_disclaimer}\n")

    console.print(f"[green]✓ Triage report exported to:[/green] [cyan]{json_path}[/cyan] and [cyan]{md_path}[/cyan]")


def main():
    parser = argparse.ArgumentParser(description="Lexiguard: Private Legal Document Triage Agent")
    parser.add_argument("--file", "-f", help="Path to local document (.pdf, .txt, .md)")
    parser.add_argument("--model", "-m", default="gemma4:e2b", help="Local Gemma model name (default: gemma4:e2b)")
    parser.add_argument("--export", "-e", action="store_true", help="Export results to JSON and Markdown")
    parser.add_argument("--audit", action="store_true", help="Verify offline network isolation environment")

    args = parser.parse_args()
    print_banner()

    if args.audit:
        is_isolated, msg = PrivacyGuard.verify_offline_environment()
        status = "[bold green]ISOLATED (Air-Gapped)[/bold green]" if is_isolated else "[yellow]CONNECTED[/yellow]"
        console.print(f"Network Status: {status} - {msg}")
        return

    if not args.file:
        console.print("[yellow]Usage:[/yellow] python -m lexiguard.cli --file <path_to_document>")
        console.print("[dim]Example: python -m lexiguard.cli --file sample_documents/residential_lease_agreement.txt[/dim]")
        return

    agent = LexiguardAgent(model_name=args.model)
    console.print(f"[cyan]Initiating on-device triage with model: [bold]{args.model}[/bold]...[/cyan]")
    
    report = agent.triage_document(args.file)
    render_triage_dashboard(report)

    if args.export:
        base = os.path.splitext(args.file)[0]
        export_report(report, base)


if __name__ == "__main__":
    main()
