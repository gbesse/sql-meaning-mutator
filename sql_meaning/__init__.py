"""Find small relational witnesses distinguishing two read-only SQLite queries."""

from .engine import search, compare

__all__ = ["search", "compare"]
