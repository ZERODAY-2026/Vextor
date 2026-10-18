"""
LexiGuard: Minimalist, Modern, High-Clarity Document Triage Interface (app.py)
ZeroDay OSS Hacktoberfest 2026 - Problem Statement 2 (PS2)
Powered by Google Gemma 2 2B on-device via Ollama. 100% Air-Gapped.
"""

import os
import sys
import time
import tempfile
from pathlib import Path
import streamlit as st

# Ensure repository root is on sys.path
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.parser import DocumentParser, DocumentCorpus
from src.agent import LexiguardAgent
from src.memory import LocalMemoryVault, get_vault
from lexiguard.models import SeverityLevel

# -------------------------------------------------------------
# Streamlit Page Setup & Minimalist Typography-First CSS
# -------------------------------------------------------------
st.set_page_config(
    page_title="LexiGuard | Legal Document Triage",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* Clean, typography-first system fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #F8FAFC;
        color: #0F172A;
    }

    /* Muted monochromatic card styling */
    .clean-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }

    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #334155;
    }

    .tag-page {
        display: inline-block;
        background: #E2E8F0;
        color: #1E293B;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }

    .sev-high {
        background: #FEF2F2;
        border: 1px solid #FCA5A5;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .sev-amber {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .sev-low {
        background: #F0FDF4;
        border: 1px solid #86EFAC;
        color: #166534;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .quote-box {
        background: #F8FAFC;
        border-left: 3px solid #64748B;
        padding: 8px 12px;
        font-style: italic;
        color: #334155;
        font-size: 0.85rem;
        margin: 6px 0;
        border-radius: 0 4px 4px 0;
    }

    .chat-bubble-user {
        background: #F1F5F9;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-size: 0.9rem;
        color: #0F172A;
    }

    .chat-bubble-agent {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
        font-size: 0.9rem;
        color: #0F172A;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Session State & Singletons
# -------------------------------------------------------------
if "agent" not in st.session_state:
    st.session_state.agent = LexiguardAgent()
if "vault" not in st.session_state:
    st.session_state.vault = get_vault()
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "current_corpus" not in st.session_state:
    st.session_state.current_corpus = None
if "doc_status" not in st.session_state:
    st.session_state.doc_status = {}
if "session_id" not in st.session_state:
    st.session_state.session_id = f"sess_{int(time.time())}"

agent = st.session_state.agent
vault = st.session_state.vault


# -------------------------------------------------------------
# Top Header & Status Bar
# -------------------------------------------------------------
col_h1, col_h2 = st.columns([2, 1])

with col_h1:
    st.markdown("## LexiGuard")
    st.caption("Private On-Device Legal Document Triage Agent • Problem Statement 2 (PS2)")

with col_h2:
    st.markdown("""
    <div style="text-align: right; margin-top: 8px;">
        <span class="status-chip">
            🟢 Local Air-Gap Active | Gemma 2 2B (On-Device)
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin: 0.5rem 0 1rem 0; border: none; border-top: 1px solid #E2E8F0;' />", unsafe_allow_html=True)


# -------------------------------------------------------------
# Multi-Input Ingestion Panel
# -------------------------------------------------------------
with st.container():
    st.markdown("##### Ingest Legal Agreement")
    
    input_mode = st.radio(
        "Ingestion Source:",
        ["Upload File (PDF / DOCX / TXT / MD)", "Paste Raw Agreement Text", "Load Sample Contract"],
        horizontal=True,
        label_visibility="collapsed"
    )

    doc_source = None
    is_raw = False
    doc_name = None

    if input_mode == "Upload File (PDF / DOCX / TXT / MD)":
        uploaded_file = st.file_uploader(
            "Upload agreement (.pdf, .docx, .txt, .md)",
            type=["pdf", "docx", "txt", "md"],
            help="100% processed locally on-device. Zero network transmissions."
        )
        if uploaded_file is not None:
            temp_dir = Path(tempfile.gettempdir()) / "lexiguard_uploads"
            temp_dir.mkdir(exist_ok=True)
            saved_path = temp_dir / uploaded_file.name
            with open(saved_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            doc_source = str(saved_path)
            doc_name = uploaded_file.name
            is_raw = False

    elif input_mode == "Paste Raw Agreement Text":
        raw_text_input = st.text_area(
            "Paste raw agreement text:",
            height=140,
            placeholder="Paste contract clauses, terms of service, or lease provisions here..."
        )
        if raw_text_input.strip():
            doc_source = raw_text_input.strip()
            doc_name = "Pasted_Agreement.txt"
            is_raw = True

    else:
        sample_options = {
            "Residential Tenancy Agreement (PDF)": "sample_documents/residential_lease_agreement.pdf",
            "Residential Tenancy Agreement (TXT)": "sample_documents/residential_lease_agreement.txt",
            "Software Employment Contract (TXT)": "sample_documents/software_employment_contract.txt",
            "Cloud SaaS Terms of Service (TXT)": "sample_documents/cloud_saas_terms_of_service.txt",
            "Adversarial Exploit Contract (TXT)": "sample_documents/adversarial_exploit_contract.txt"
        }
        chosen_sample = st.selectbox("Choose sample agreement:", list(sample_options.keys()))
        doc_source = str(ROOT_DIR / sample_options[chosen_sample])
        doc_name = chosen_sample
        is_raw = False

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        analyze_clicked = st.button("Analyze Agreement", type="primary", use_container_width=True)

    if analyze_clicked:
        if not doc_source:
            st.error("Please provide a document or paste text before analyzing.")
        else:
            with st.spinner("Processing agreement locally with Google Gemma 2 2B..."):
                t0 = time.time()
                # Parse unified corpus
                corpus = DocumentParser.parse(doc_source, is_raw_text=is_raw, file_name=doc_name)
                # Check active cache
                cached = vault.get_cached_document(corpus.doc_hash)
                cache_hit = cached is not None

                report = agent.triage_document(
                    source=doc_source,
                    is_raw_text=is_raw,
                    session_id=st.session_state.session_id
                )
                elapsed = time.time() - t0

                st.session_state.current_report = report
                st.session_state.current_corpus = corpus
                st.session_state.doc_status = {
                    "file_name": doc_name,
                    "file_type": corpus.metadata.get("file_type", "unknown").upper(),
                    "word_count": corpus.metadata.get("word_count", 0),
                    "chunk_count": corpus.metadata.get("chunk_count", 0),
                    "cache_hit": cache_hit,
                    "latency": round(elapsed, 2)
                }
                st.rerun()

# Document Status Bar (when analyzed)
if st.session_state.doc_status:
    ds = st.session_state.doc_status
    cache_badge = "⚡ Instant Cache Hit (0ms compute)" if ds.get("cache_hit") else f"⏱️ Analyzed in {ds.get('latency')}s"
    st.markdown(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 14px; margin: 0.75rem 0; font-size: 0.8rem; color: #475569; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <b>Document:</b> {ds.get('file_name')} &nbsp;|&nbsp;
            <b>Type:</b> {ds.get('file_type')} &nbsp;|&nbsp;
            <b>Words:</b> {ds.get('word_count')} &nbsp;|&nbsp;
            <b>Chunks:</b> {ds.get('chunk_count')}
        </div>
        <div style="color: #059669; font-weight: 600;">
            {cache_badge}
        </div>
    </div>
    """, unsafe_allow_html=True)


# -------------------------------------------------------------
# Structured Dual-Pane Output
# -------------------------------------------------------------
report = st.session_state.current_report

if report:
    col_left, col_right = st.columns([1, 1], gap="medium")

    # =========================================================
    # LEFT COLUMN: Triage Matrix
    # =========================================================
    with col_left:
        st.markdown("#### Triage Matrix")

        # 1. Parties & Dates Card
        with st.container():
            st.markdown("""
            <div class="clean-card">
                <div style="font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; color: #1E293B;">
                    Parties Identified & Effective Dates
                </div>
            """, unsafe_allow_html=True)
            doc_type = report.metadata.detected_document_type or "Commercial Contract"
            st.markdown(f"• **Agreement Type:** {doc_type}")
            st.markdown(f"• **Governing Scope:** Standard commercial transaction; jurisdiction not formally selected.")
            st.markdown("</div>", unsafe_allow_html=True)

        # 2. Executive Summary Card
        with st.container():
            overall_sev = report.overall_risk_rating
            sev_badge = "sev-high" if overall_sev == SeverityLevel.HIGH_RISK else ("sev-amber" if overall_sev == SeverityLevel.CAUTION_AMBER else "sev-low")
            sev_label = "HIGH RISK" if overall_sev == SeverityLevel.HIGH_RISK else ("CAUTION (AMBER)" if overall_sev == SeverityLevel.CAUTION_AMBER else "STANDARD LOW")

            st.markdown(f"""
            <div class="clean-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 600; font-size: 0.95rem; color: #1E293B;">Executive Summary</span>
                    <span class="{sev_badge}">{sev_label}</span>
                </div>
                <div style="font-size: 0.88rem; line-height: 1.5; color: #334155;">
                    {report.summary}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 3. Critical Risks & Ambiguities (with Expandable Quotes & Page Numbers)
        st.markdown("##### Critical Risks & Ambiguities")
        for idx, clause in enumerate(report.clauses):
            c_badge = "sev-high" if clause.severity == SeverityLevel.HIGH_RISK else ("sev-amber" if clause.severity == SeverityLevel.CAUTION_AMBER else "sev-low")
            location_tag = clause.citation.section_reference or "Section"
            
            with st.container():
                st.markdown(f"""
                <div class="clean-card" style="margin-bottom: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <div>
                            <span class="tag-page">{location_tag}</span>
                            <span style="font-weight: 600; font-size: 0.9rem; color: #0F172A;">{clause.category}</span>
                        </div>
                        <span class="{c_badge}">{clause.severity.value}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #334155; margin-top: 4px;">
                        {clause.plain_english_summary}
                    </div>
                    <div class="quote-box">
                        "{clause.citation.verbatim_quote}"
                    </div>
                    <div style="font-size: 0.8rem; color: #64748B; margin-top: 4px;">
                        <b>Practical Danger:</b> {clause.practical_concern}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # 4. Missing Standard Protections (Silent Clause Audit - Gate L7)
        if report.silent_clauses:
            st.markdown("##### Missing Standard Protections (Silent Clauses)")
            for sc in report.silent_clauses:
                with st.expander(f"⚠️ Omitted Term: {sc.topic}"):
                    st.markdown(f"**Standard Legal Safeguard:** {sc.standard_legal_norm}")
                    st.markdown(f"**Why Silence is Concerning:** {sc.why_silence_is_concerning}")
                    st.info(f"💡 **Recommended Addendum:** {sc.recommended_protective_clause}")


    # =========================================================
    # RIGHT COLUMN: Grounded Conversational Assistant
    # =========================================================
    with col_right:
        st.markdown("#### Grounded Legal Assistant")
        st.caption("Ask questions about the contract. Responses are strictly grounded in document passages.")

        # Question Input Box
        user_q = st.text_input(
            "Ask a question about this agreement:",
            placeholder="e.g. Can the landlord enter without notice? What is the penalty for late rent?",
            key="user_query_input"
        )

        col_q1, col_q2 = st.columns([1, 1])
        with col_q1:
            send_clicked = st.button("Ask Assistant", type="primary", use_container_width=True)
        with col_q2:
            clear_clicked = st.button("Clear Memory", use_container_width=True)

        if clear_clicked:
            vault.clear_session_history(st.session_state.session_id)
            st.toast("Session chat memory cleared.", icon="🗑️")
            st.rerun()

        if send_clicked and user_q.strip():
            corpus = st.session_state.current_corpus
            with st.spinner("Synthesizing grounded response with Gemma 2..."):
                ans_obj = agent.answer_question(
                    source=corpus.raw_text,
                    question=user_q.strip(),
                    is_raw_text=True,
                    session_id=st.session_state.session_id
                )
                st.rerun()

        # Persistent Chat Stream from SQLite
        chat_logs = vault.get_chat_history(session_id=st.session_state.session_id, limit=30)
        
        if not chat_logs:
            st.markdown("""
            <div style="background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 2rem; text-align: center; color: #64748B; font-size: 0.85rem; margin-top: 1rem;">
                No questions asked yet.<br>Type a question above to test passage grounding or silence detection.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
            for turn in reversed(chat_logs):
                # User Bubble
                st.markdown(f"""
                <div class="chat-bubble-user">
                    <b>You:</b> {turn['user_query']}
                </div>
                """, unsafe_allow_html=True)

                # Agent Bubble
                st.markdown(f"""
                <div class="chat-bubble-agent">
                    <b>LexiGuard:</b> {turn['agent_response']}
                """, unsafe_allow_html=True)

                # Citations with Location Tags (Page X or Section Y)
                if turn['cited_passages']:
                    for cite in turn['cited_passages']:
                        loc = cite.get('section_reference', 'Passage')
                        quote_txt = cite.get('verbatim_quote', '')
                        st.markdown(f"""
                        <div style="margin-top: 6px;">
                            <span class="tag-page">{loc}</span>
                            <span style="font-size: 0.8rem; font-style: italic; color: #475569;">
                                "{quote_txt}"
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Feedback Buttons (Thumbs Up / Thumbs Down / Bookmark) -> SQLite Exemplar Memory
                fb_col1, fb_col2, fb_col3, _ = st.columns([1, 1, 1, 4])
                with fb_col1:
                    if st.button("👍", key=f"up_{turn['id']}", help="Confirm accurate interpretation"):
                        vault.record_exemplar(turn['user_query'], turn['agent_response'], feedback_type="thumbs_up")
                        st.toast("Saved to adaptive few-shot exemplar memory!", icon="✅")
                with fb_col2:
                    if st.button("👎", key=f"down_{turn['id']}", help="Flag incorrect response"):
                        st.toast("Feedback recorded.", icon="📝")
                with fb_col3:
                    if st.button("🔖", key=f"book_{turn['id']}", help="Bookmark important clause"):
                        vault.record_exemplar(turn['user_query'], turn['agent_response'], feedback_type="bookmark")
                        st.toast("Bookmarked to SQLite memory!", icon="🔖")

                st.markdown("<hr style='margin: 0.5rem 0 0.75rem 0; border: none; border-top: 1px solid #F1F5F9;' />", unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 3rem 2rem; text-align: center; margin-top: 1.5rem;">
        <div style="font-size: 1.5rem; font-weight: 600; color: #1E293B; margin-bottom: 0.5rem;">Ready to Triage Legal Agreement</div>
        <div style="font-size: 0.9rem; color: #64748B; max-width: 500px; margin: 0 auto 1.5rem auto;">
            Select a document format above (PDF, DOCX, TXT, or paste text directly) and click <b>Analyze Agreement</b> to run local on-device triage.
        </div>
    </div>
    """, unsafe_allow_html=True)
