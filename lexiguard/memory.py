"""
Lexiguard Memory & Persistence
Re-exports LocalMemoryVault and helpers from src.memory for package consistency.
"""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
_ROOT_DIR = str(Path(__file__).parent.parent.resolve())
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from src.memory import LocalMemoryVault, get_vault, DEFAULT_DB_PATH

__all__ = ["LocalMemoryVault", "get_vault", "DEFAULT_DB_PATH"]
