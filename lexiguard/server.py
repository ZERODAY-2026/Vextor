"""
Lexiguard Local Privacy-First Web Dashboard
Pure Python standard library http.server with self-contained HTML/CSS/JS frontend.
Guarantees 100% on-device local execution with zero external CDN dependencies.
"""

import http.server
import socketserver
import json
import os
import urllib.parse
from .agent import LexiguardAgent

PORT = 8080

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Lexiguard | Private Legal Document Triage Agent</title>
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-surface: #111827;
      --bg-glass: rgba(17, 24, 39, 0.75);
      --border-color: rgba(255, 255, 255, 0.1);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --accent-cyan: #06b6d4;
      --accent-blue: #3b82f6;
      --risk-high: #ef4444;
      --risk-amber: #f59e0b;
      --risk-low: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: radial-gradient(circle at 50% 0%, #1e293b 0%, var(--bg-primary) 70%);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      padding: 1.5rem 2rem;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-glass);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .logo-group { display: flex; align-items: center; gap: 0.75rem; }
    .logo-badge {
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
      padding: 0.4rem 0.8rem;
      border-radius: 8px;
      font-weight: 800;
      font-size: 1.1rem;
      letter-spacing: 0.5px;
    }
    .privacy-tag {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.4);
      color: #34d399;
      padding: 0.35rem 0.85rem;
      border-radius: 20px;
      font-size: 0.82rem;
      font-weight: 600;
    }
    main {
      flex: 1;
      max-width: 1200px;
      width: 100%;
      margin: 2rem auto;
      padding: 0 1.5rem;
    }
    .banner {
      background: rgba(245, 158, 11, 0.1);
      border-left: 4px solid var(--risk-amber);
      padding: 1rem 1.25rem;
      border-radius: 6px;
      margin-bottom: 2rem;
      font-size: 0.9rem;
      color: #fbbf24;
    }
    .upload-card {
      background: var(--bg-surface);
      border: 2px dashed var(--border-color);
      border-radius: 16px;
      padding: 3rem 2rem;
      text-align: center;
      transition: all 0.25s ease;
      cursor: pointer;
      margin-bottom: 2rem;
    }
    .upload-card:hover {
      border-color: var(--accent-cyan);
      box-shadow: 0 0 25px rgba(6, 182, 212, 0.15);
    }
    .btn-sample {
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.5rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.85rem;
      transition: background 0.2s;
      margin: 0.25rem;
    }
    .btn-sample:hover {
      background: rgba(6, 182, 212, 0.25);
      border-color: var(--accent-cyan);
    }
    .results-container { display: none; margin-top: 2rem; }
    .card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 0.75rem;
    }
    .risk-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .risk-HIGH_RISK { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
    .risk-CAUTION_AMBER { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }
    .risk-STANDARD_LOW { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }
    .clause-card {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }
    .clause-meta { display: flex; justify-content: space-between; margin-bottom: 0.5rem; }
    .tier-box {
      margin-top: 0.75rem;
      padding: 0.75rem;
      background: rgba(0, 0, 0, 0.2);
      border-radius: 6px;
      font-size: 0.9rem;
    }
    .quote-box {
      margin-top: 0.75rem;
      font-style: italic;
      color: #94a3b8;
      border-left: 3px solid var(--accent-cyan);
      padding-left: 0.75rem;
      font-size: 0.85rem;
    }
    footer {
      text-align: center;
      padding: 1.5rem;
      border-top: 1px solid var(--border-color);
      color: var(--text-muted);
      font-size: 0.8rem;
    }
  </style>
</head>
<body>
  <header>
    <div class="logo-group">
      <div class="logo-badge">⚖️ LEXIGUARD</div>
      <span style="font-weight: 500; color: #94a3b8;">Private Legal Triage Agent</span>
    </div>
    <div class="privacy-tag">
      <span style="font-size: 1rem;">🔒</span> 100% On-Device Air-Gapped (Gemma)
    </div>
  </header>

  <main>
    <div class="banner">
      <strong>⚠️ Legal Boundary Notice:</strong> Lexiguard is an AI-powered preliminary document comprehension tool. It is not a lawyer, cannot provide legal advice, and does not determine legal validity or enforceability.
    </div>

    <div class="upload-card" id="drop-area" onclick="document.getElementById('file-input').click()">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📄</div>
      <h2 style="margin-bottom: 0.5rem;">Select or Drag Legal Document</h2>
      <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">Supports PDF (.pdf) and Plain Text (.txt, .md) • Processed 100% locally on this machine</p>
      <input type="file" id="file-input" style="display:none;" onchange="handleFileSelect(event)">
      
      <div style="margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
        <span style="font-size: 0.85rem; color: var(--text-muted);">Or try a sample document:</span><br>
        <button class="btn-sample" onclick="loadSample('residential_lease', event)">🏠 Residential Tenancy</button>
        <button class="btn-sample" onclick="loadSample('software_employment', event)">💼 Employment Contract</button>
        <button class="btn-sample" onclick="loadSample('saas_terms', event)">☁️ SaaS Agreement</button>
      </div>
    </div>

    <div id="loading" style="display:none; text-align:center; padding: 3rem;">
      <div style="font-size: 2.5rem; margin-bottom: 1rem;">⚙️</div>
      <h3 style="color: var(--accent-cyan);">Performing On-Device Gemma Triage...</h3>
      <p style="color: var(--text-muted); margin-top: 0.5rem;">Grounding citations • Auditing silent clauses • Monitoring zero network calls</p>
    </div>

    <div class="results-container" id="results">
      <!-- Executive Summary -->
      <div class="card">
        <div class="card-header">
          <div>
            <h2 id="doc-title">Document Title</h2>
            <span id="doc-type" style="color: var(--accent-cyan); font-size: 0.9rem;">Agreement</span>
          </div>
          <div id="overall-badge" class="risk-badge risk-HIGH_RISK">HIGH RISK</div>
        </div>
        <p id="exec-summary" style="line-height: 1.6; font-size: 0.98rem;"></p>
      </div>

      <!-- Clauses Section -->
      <div class="card">
        <h3 style="margin-bottom: 1rem; color: var(--accent-cyan);">Key Clauses Breakdown (Grounding & 3-Tier Analysis)</h3>
        <div id="clauses-list"></div>
      </div>

      <!-- Silent Clauses -->
      <div class="card">
        <h3 style="margin-bottom: 1rem; color: var(--risk-amber);">Audit of Silent & Missing Clauses</h3>
        <div id="silents-list"></div>
      </div>

      <!-- Escalations -->
      <div class="card">
        <h3 style="margin-bottom: 1rem; color: #a78bfa;">Safe Escalation Checklist (Questions for Counsel)</h3>
        <div id="escalations-list"></div>
      </div>
    </div>
  </main>

  <footer>
    ZeroDay OSS Hacktoberfest 2026 | Problem Statement 2: Private Legal Document Triage Agent | Fully Open Source (Apache-2.0)
  </footer>

  <script>
    async function loadSample(sampleType, event) {
      event.stopPropagation();
      document.getElementById('loading').style.display = 'block';
      document.getElementById('results').style.display = 'none';

      try {
        const res = await fetch('/api/triage_sample?type=' + sampleType);
        const report = await res.json();
        renderReport(report);
      } catch (err) {
        alert('Triage Error: ' + err.message);
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    }

    async function handleFileSelect(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('document', file);

      document.getElementById('loading').style.display = 'block';
      document.getElementById('results').style.display = 'none';

      try {
        const res = await fetch('/api/upload_triage', { method: 'POST', body: formData });
        const report = await res.json();
        renderReport(report);
      } catch (err) {
        alert('Triage Error: ' + err.message);
      } finally {
        document.getElementById('loading').style.display = 'none';
      }
    }

    function renderReport(report) {
      document.getElementById('doc-title').innerText = report.metadata.filename;
      document.getElementById('doc-type').innerText = report.metadata.detected_document_type + " • Parties: " + (report.metadata.identified_parties.join(', ') || 'Standard');
      
      const badge = document.getElementById('overall-badge');
      badge.className = 'risk-badge risk-' + report.overall_risk_rating;
      badge.innerText = report.overall_risk_rating.replace('_', ' ');

      document.getElementById('exec-summary').innerText = report.executive_summary;

      // Render clauses
      const clList = document.getElementById('clauses-list');
      clList.innerHTML = '';
      report.clauses.forEach(c => {
        const item = document.createElement('div');
        item.className = 'clause-card';
        item.innerHTML = `
          <div class="clause-meta">
            <strong>${c.clause_id}: ${c.category}</strong>
            <span class="risk-badge risk-${c.severity}">${c.severity.replace('_', ' ')}</span>
          </div>
          <p style="margin-bottom: 0.5rem; color: #e2e8f0;">${c.plain_language_summary}</p>
          <div class="tier-box">
            <strong>Literal Text:</strong> ${c.explicit_statement}<br>
            <strong style="color: #60a5fa;">Interpretation:</strong> ${c.potential_interpretation}<br>
            <strong style="color: #f87171;">Concern/Trap:</strong> ${c.practical_concern}
          </div>
          <div class="quote-box">"${c.citation.verbatim_quote}" [${c.citation.section_reference || 'Cited'}]</div>
        `;
        clList.appendChild(item);
      });

      // Render silent clauses
      const sList = document.getElementById('silents-list');
      sList.innerHTML = '';
      if (!report.silent_clauses || report.silent_clauses.length === 0) {
        sList.innerHTML = '<p style="color: #94a3b8;">No major standard protections detected as silent.</p>';
      } else {
        report.silent_clauses.forEach(s => {
          const item = document.createElement('div');
          item.className = 'clause-card';
          item.innerHTML = `
            <strong>❌ Silent Protection: ${s.topic}</strong>
            <p style="color: #fbbf24; margin-top: 0.25rem;">${s.risk_implication}</p>
            <p style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.25rem;"><em>Action: ${s.suggested_inquiry}</em></p>
          `;
          sList.appendChild(item);
        });
      }

      // Render escalations
      const eList = document.getElementById('escalations-list');
      eList.innerHTML = '';
      report.escalations.forEach(e => {
        const item = document.createElement('div');
        item.className = 'clause-card';
        const qList = e.specific_questions_for_counsel.map(q => '<li>' + q + '</li>').join('');
        item.innerHTML = `
          <strong>${e.trigger_clause} — Consult: <span style="color: #34d399;">${e.recommended_specialist}</span></strong>
          <p style="color: #cbd5e1; margin-top: 0.25rem;">${e.risk_description}</p>
          <ul style="margin: 0.5rem 0 0 1.5rem; font-size: 0.9rem; color: #94a3b8;">${qList}</ul>
        `;
        eList.appendChild(item);
      });

      document.getElementById('results').style.display = 'block';
    }
  </script>
</body>
</html>
"""


class LexiguardRequestHandler(http.server.BaseHTTPRequestHandler):
    """Local-only HTTP Request Handler."""

    agent = LexiguardAgent()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif parsed.path == "/api/triage_sample":
            params = urllib.parse.parse_qs(parsed.query)
            sample_type = params.get("type", ["residential_lease"])[0]
            
            sample_file_map = {
                "residential_lease": "sample_documents/residential_lease_agreement.txt",
                "software_employment": "sample_documents/software_employment_contract.txt",
                "saas_terms": "sample_documents/cloud_saas_terms_of_service.txt"
            }
            sample_path = sample_file_map.get(sample_type, "sample_documents/residential_lease_agreement.txt")
            
            # Run local triage
            try:
                report = self.agent.triage_document(sample_path)
                data = report.model_dump()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server(port: int = PORT):
    """Starts the local web server on localhost."""
    server_address = ("127.0.0.1", port)
    with socketserver.TCPServer(server_address, LexiguardRequestHandler) as httpd:
        print(f"⚖️ Lexiguard Web UI running at: http://127.0.0.1:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
