import time
import os
import sys
import psutil

# Ensure package root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lexiguard.agent import LexiguardAgent


def run_benchmark():
    print("=" * 60)
    print("⚖️  LEXIGUARD PERFORMANCE & MEMORY BENCHMARK")
    print("=" * 60)

    proc = psutil.Process(os.getpid())
    agent = LexiguardAgent()

    test_docs = [
        ("Residential Tenancy", "sample_documents/residential_lease_agreement.txt"),
        ("Employment Contract", "sample_documents/software_employment_contract.txt"),
        ("Cloud SaaS Terms", "sample_documents/cloud_saas_terms_of_service.txt")
    ]

    print(f"Hardware Environment: {psutil.cpu_count(logical=False)} Cores / {psutil.cpu_count(logical=True)} Threads")
    total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
    print(f"System RAM: {total_ram_gb} GB")
    print("-" * 60)

    for doc_name, path in test_docs:
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        word_count = len(content.split())
        start_mem_mb = proc.memory_info().rss / (1024 * 1024)
        
        t0 = time.time()
        report = agent.triage_document(path)
        elapsed = time.time() - t0
        
        end_mem_mb = proc.memory_info().rss / (1024 * 1024)
        mem_delta_mb = round(end_mem_mb - start_mem_mb, 2)
        words_per_sec = round(word_count / elapsed, 1) if elapsed > 0 else 0

        print(f"📄 Document: {doc_name} ({word_count} words)")
        print(f"   ⏱️  Total Latency: {elapsed:.2f} s")
        print(f"   ⚡ Processing Speed: {words_per_sec} words/sec")
        print(f"   🧠 Process Memory (RSS): {end_mem_mb:.1f} MB (Delta: {mem_delta_mb:+.1f} MB)")
        print(f"   🎯 Clauses Analyzed: {len(report.clauses)}")
        print(f"   🔍 Silent Clauses Detected: {len(report.silent_clauses)}")
        print(f"   🛡️  Privacy Status: {report.privacy_audit.get('compliance_status')}")
        print("-" * 60)

    print("✓ Benchmark completed successfully. Output demonstrates on-device memory and latency envelope.")


if __name__ == "__main__":
    run_benchmark()
