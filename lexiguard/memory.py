"""
Lexiguard Memory & Persistence
Re-exports LocalMemoryVault and helpers from src.memory for package consistency.
"""

from src.memory import LocalMemoryVault, get_vault, DEFAULT_DB_PATH

__all__ = ["LocalMemoryVault", "get_vault", "DEFAULT_DB_PATH"]
