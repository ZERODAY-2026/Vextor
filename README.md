# PS2 — Agentic AI: Private Legal Document Triage Agent

[![ZeroDay OSS Hacktoberfest 2026](https://img.shields.io/badge/ZeroDay_OSS-Hacktoberfest_2026_PS2-cyan.svg)](https://iiitdwd.ac.in)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![LLM: Google Gemma Edge](https://img.shields.io/badge/LLM-Google_Gemma_2_(2B)-green.svg)](https://ollama.com)
[![Privacy: 100% On-Device](https://img.shields.io/badge/Privacy-100%25_On--Device_Local-brightgreen.svg)](#-privacy-guarantee--network-isolation-l9)
[![UI: Streamlit Studio](https://img.shields.io/badge/UI-Streamlit_Studio-red.svg)](#-streamlit-studio-ui)
[![Status: Unified Package](https://img.shields.io/badge/Package-lexiguard_CLI_%26_GUI-orange.svg)](#-unified-software-packaging)

**Project Name:** Lexiguard  
**Track:** Problem Statement 2 (PS2) — Agentic AI: Private Legal Document Triage Agent  
**Event:** ZeroDay OSS Hacktoberfest 2026, IIIT Dharwad  
**Repository:** [https://github.com/abhisheksingh1729/lexiguard](https://github.com/abhisheksingh1729/lexiguard)

---

## 📌 Executive Overview & Problem Statement

Legal documents—such as residential tenancy agreements, employment contracts, nondisclosure agreements (NDAs), and terms of service—are dense with archaic legal terminology, unilateral obligations, hidden traps, and severe financial liabilities. For ordinary consumers, tenants, and employees, professional legal review for preliminary queries is expensive, time-consuming, and often inaccessible.

### The Challenge
Build a **privacy-first, fully on-device AI agent** powered by a **Google Gemma edge model** that can:
1. Ingest real-world legal documents locally (PDF or plain text).
2. Translate complex legalese into clear, plain language without distortion.
3. Highlight unbalanced obligations, one-sided penalties, and termination traps.
4. Conspicuously detect **silent clauses** (essential legal protections that are missing).
5. Ground every finding in identifiable, verbatim source passages.
6. Strictly avoid presenting output as legal advice and safely escalate to licensed attorneys.
7. Package all components into a unified, installable desktop utility software with modern GUI.

---

## 🛡️ Core Architectural Principles (PS2 Alignment)

| PS2 Mandate | Meaning & Implementation in Lexiguard | Status |
| :--- | :--- | :---: |
| **On-Device Privacy (L9)** | 100% of document parsing, chunking, and LLM inference stays on localhost. No cloud models, remote APIs, or telemetry. | ✅ Verified |
| **Google Gemma Edge (L10)** | Powered by Google Gemma 2 (2B) (`gemma2:2b`) running locally via Ollama with dynamic runtime auto-discovery. | ✅ Integrated |
| **3-Tier Clause Breakdown (L6)** | Strictly separates: (1) Literal Statement, (2) Practical Interpretation, and (3) Practical Concern/Risk. | ✅ Built |
| **Source Grounding (L5)** | Verbatim quotes verified against original source text; flags when the document is silent. | ✅ Verified |
| **Silent Clause Audit (L7)** | Audits critical missing protections (e.g., notice periods, cure windows, deposit refund timelines). | ✅ Built |
| **Safe Legal Escalation (L8)** | Refuses enforceability and legality verdicts; formulates precise escalation questions for licensed legal counsel. | ✅ Built |
| **Unified Packaging** | Consolidated into a single `lexiguard` CLI command suite and Streamlit Studio application. | ✅ Completed |

---

## 💻 Streamlit Studio UI

Lexiguard features a modern, dark-themed, cyber-legal **Streamlit Studio** dashboard designed with glassmorphism aesthetics and micro-animations.

### Key Studio Modules:
1. **📋 Document Triage & Clause Auditor (Gates L1–L4, L6):**
   - Drag-and-drop ingestion for PDF and TXT contracts.
   - Overall Risk Score gauge (High Risk, Caution Amber, Low Risk).
   - Plain-English Executive Summary written for non-lawyers.
   - Filterable 3-tier clause breakdown with verbatim quotes and practical dangers.
   - Silent clause audit highlighting omitted statutory protections.
   - 1-click JSON and Markdown report export.
2. **💬 Grounded Legal Q&A (Gates L5, L7, L8):**
   - Ask natural language questions with 100% verbatim passage citations (L5).
   - Silence detector: explicitly alerts when a topic is omitted from the contract (L7).
   - Enforceability guard: refuses court legality determinations and directs to legal aid (L8).
3. **⚖️ Contract Diff & Redlining Agent:**
   - Compares Draft A vs Draft B (e.g., original lease vs landlord's revised draft).
   - Detects stealth amendments, added tenant restrictions, and removed protections.
   - Calculates net asymmetric risk shift percentage.
4. **🛡️ Air-Gap Privacy & Socket Monitor (Gate L9):**
   - Live socket audit confirming 0 remote outbound connections.
   - Export signed `privacy_audit.json` cryptographic evidence for hackathon judges.
5. **🏆 Judges 10-Gate Evaluation Suite:**
   - 1-click interactive evaluation runner testing all 10 rubric gates in real-time.

---

## 📦 Unified Software Packaging

All modular components are consolidated under the unified `lexiguard` console command and Python package:

```
lexiguard
├── ui         Launch the interactive Streamlit Studio UI
├── triage     Analyze a legal contract (.pdf or .txt) for risks and missing clauses
├── ask        Ask a grounded question with strict verbatim citations (L5)
├── compare    Perform two-version semantic diff redlining (Draft A vs Draft B)
├── demo       Execute the turnkey 10-gate judge evaluation suite
├── audit      Verify air-gap isolation and generate signed socket proof
├── web        Launch the lightweight zero-dependency local HTTP web server
└── benchmark  Measure on-device latency, token speed, and RAM envelope
```

---

## ⚡ Quickstart Guide

### 1. Clone & Install
```powershell
git clone https://github.com/abhisheksingh1729/lexiguard.git
cd lexiguard
pip install -e .
```
*(Or install requirements directly: `pip install -r requirements.txt`)*

### 2. Pull Google Gemma 2 Model
Ensure [Ollama](https://ollama.com) is installed and running locally:
```powershell
ollama pull gemma2:2b
```

### 3. Launch Streamlit Studio (Modern Web UI)
```powershell
lexiguard ui
# Or directly via streamlit:
streamlit run streamlit_app.py
```
Open your browser at **`http://localhost:8501`**.

### 4. Run Turnkey Judge Demonstration (Recommended for Evaluators)
```powershell
lexiguard demo
# Or standalone:
python demo_judge.py
```

### 5. Unified CLI Usage Examples
```powershell
# 1. Triage a PDF contract with JSON & Markdown export
lexiguard triage sample_documents/residential_lease_agreement.pdf --export

# 2. Ask a grounded question with verbatim citations
lexiguard ask sample_documents/residential_lease_agreement.txt "Can landlord enter without notice?"

# 3. Compare two versions for stealth modifications
lexiguard compare sample_documents/residential_lease_agreement.txt sample_documents/residential_lease_revised_v2.txt

# 4. Verify air-gap isolation and export signed proof
lexiguard audit

# 5. Measure edge performance and RAM footprint
lexiguard benchmark
```

---

## 🔒 Privacy Guarantee & Network Isolation (L9)

Lexiguard enforces complete network isolation during document processing:
- **Zero Remote Calls**: All parsing, segmentation, reasoning, and summarization occur strictly on the local machine.
- **Active Socket Verification**: Built-in socket monitors verify that no document contents or derived text ever traverse the network.
- **Run the Privacy Audit**:
  ```powershell
  python -m unittest tests/test_privacy.py -v
  ```

---

## ⚠️ Important Boundary & Disclaimer (L8)

> **MANDATORY NOTICE:** Lexiguard is an AI-powered preliminary document comprehension and issue identification tool. **Lexiguard is NOT a lawyer, does NOT provide legal advice, and cannot determine the legal validity, binding nature, or enforceability of any contract.** Never execute, breach, or litigate a contract based solely on this automated output. Always consult a licensed legal practitioner or advocate in your jurisdiction for definitive legal counsel.

---

## 📄 License

Distributed under the **Apache-2.0 License**. See [`LICENSE`](LICENSE) for complete terms.
