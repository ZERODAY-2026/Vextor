# PS2 — Agentic AI: Private Legal Document Triage Agent

[![ZeroDay OSS Hacktoberfest 2026](https://img.shields.io/badge/ZeroDay_OSS-Hacktoberfest_2026_PS2-cyan.svg)](https://iiitdwd.ac.in)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![LLM: Google Gemma Edge](https://img.shields.io/badge/LLM-Google_Gemma_Edge_(E2B%2FE4B)-green.svg)](https://ollama.com)
[![Privacy: 100% On-Device](https://img.shields.io/badge/Privacy-100%25_On--Device_Local-brightgreen.svg)](#-privacy-guarantee--network-isolation-l9)
[![Checkpoint: 1](https://img.shields.io/badge/Status-Checkpoint_1_Completed-orange.svg)](#-checkpoint-1-progress--status)

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

---

## 🛡️ Core Architectural Principles (PS2 Alignment)

| PS2 Mandate | Meaning & Implementation in Lexiguard | Status |
| :--- | :--- | :---: |
| **On-Device Privacy (L9)** | 100% of document parsing, embeddings, chunking, and LLM inference stays on localhost. No cloud models, remote APIs, or telemetry. | ✅ Verified |
| **Google Gemma Edge (L10)** | Powered by Google Gemma edge models (`gemma4:e2b` / `gemma:2b`) running locally via Ollama. | ✅ Integrated |
| **3-Tier Clause Breakdown (L6)** | Strictly separates: (1) Literal Statement, (2) Practical Interpretation, and (3) Practical Concern/Risk. | ✅ Built |
| **Source Grounding (L5)** | Verbatim quotes verified against original source text; flags when the document is silent. | ✅ Verified |
| **Silent Clause Audit** | Audits critical missing protections (e.g., notice periods, cure windows, deposit refund timelines). | ✅ Built |
| **Safe Legal Escalation (L8)** | Refuses enforceability and legality verdicts; formulates precise escalation questions for licensed legal counsel. | ✅ Built |

---

## 🚀 Checkpoint 1 Progress & Status

For **Checkpoint 1**, the core functional pipeline has been implemented, validated, and verified offline:

- [x] **Local Document Parser (`LocalDocumentParser`)**: Pure offline PDF (`pypdf`) and plaintext/markdown reader with heading and clause segmentation.
- [x] **Gemma Triage Agent (`LexiguardAgent`)**: Structured 3-tier analysis engine connected to local Gemma via `ollama-python` with deterministic fallback.
- [x] **Socket-Level Privacy Auditor (`PrivacyGuard`)**: Real-time process socket monitor guaranteeing 0 outbound remote connections.
- [x] **Terminal User Interface (`lexiguard.cli`)**: Interactive, color-coded Rich CLI with risk matrices, grounded Q&A, and JSON/Markdown export.
- [x] **Localhost Web Dashboard (`lexiguard.server`)**: Self-contained, responsive local web UI (Port 8080) with glassmorphic dark-mode aesthetics.
- [x] **Automated Test Suite (`tests/`)**: 9/9 automated unit, integration, privacy, and adversarial prompt-injection tests passing.
- [x] **Open Source Deliverable**: Licensed under the official Apache-2.0 open-source license.

*(Note: Detailed Mermaid sequence diagrams, extended CUAD statutory benchmarks, and multi-document comparison charts will be expanded in subsequent checkpoints as the project progresses).*

---

## 🛠️ Technology Stack

- **Core Language:** Python 3.10+ (Tested on Python 3.15)
- **Local LLM Engine:** Google Gemma Edge Models (`gemma4:e2b` / `gemma:2b`) via Ollama (`http://localhost:11434`)
- **Python LLM Client:** `ollama-python >= 0.4.0`
- **Data Schemas & Validation:** `pydantic >= 2.7.0`
- **Document Parsing:** `pypdf >= 5.0.0`
- **CLI & Formatting:** `rich >= 13.7.0`
- **System & Network Monitoring:** `psutil >= 5.9.0`

---

## ⚡ Quickstart Guide

### 1. Clone & Set Up Environment
```powershell
git clone https://github.com/abhisheksingh1729/lexiguard.git
cd lexiguard
pip install -r requirements.txt
```

### 2. Pull Local Google Gemma Model
Ensure [Ollama](https://ollama.com) is running locally, then pull the Google Gemma edge model:
```powershell
ollama pull gemma4:e2b
# Or for ultra-low resource hardware:
ollama pull gemma:2b
```

### 3. Run Document Triage via Terminal CLI
```powershell
# Triage a sample residential lease with JSON & Markdown export
python -m lexiguard.cli --file sample_documents/residential_lease_agreement.txt --export

# Triage a software employment contract with non-compete detection
python -m lexiguard.cli --file sample_documents/software_employment_contract.txt
```

### 4. Run Grounded Q&A (Testing Citations & Document Silence)
```powershell
# Ask a question answered by the contract (verbatim citation)
python -m lexiguard.cli --file sample_documents/residential_lease_agreement.txt --ask "Can the landlord enter without notice?"

# Ask a question on an omitted topic (document silence detection)
python -m lexiguard.cli --file sample_documents/residential_lease_agreement.txt --ask "Does the lease allow pets?"
```

### 5. Launch the Local Web Dashboard
```powershell
python -m lexiguard.server
```
Navigate to **`http://localhost:8080`** in your browser.

### 6. Run the Automated Test Suite
```powershell
python -m unittest discover tests -v
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
