"""
Lexiguard Streamlit Studio Module Wrapper
Direct entry point for running Streamlit from within the package: `streamlit run -m lexiguard.app`
"""

import sys
from pathlib import Path

# Redirect to the root app.py (modern minimalist light-slate interface)
root_app = Path(__file__).parent.parent / "app.py"
if not root_app.exists():
    root_app = Path(__file__).parent.parent / "streamlit_app.py"

if root_app.exists():
    with open(root_app, "r", encoding="utf-8") as f:
        code = f.read()
    exec(code)
else:
    raise FileNotFoundError(f"Could not locate {root_app}")
