"""
Audit structured preprocessing fields for likely tag-driven false positives.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .hybrid_search import DATA_STRUCTURE_TERMS, TERM_ALIASES


def _contains_any(text: str, aliases: list[str]) -> bool:
    t = (text or "").lower()
    return any(alias.lower() in t for alias in aliases)


def _evidence(row: dict, term: str) -> tuple[bool, bool, bool]:
    aliases = TERM_ALIASES.get(term, [term])
    trusted = f"{row.get('title', '')}\n{row.get('content', '')}"
    weak = f"{row.get('tags', '')}\n{row.get('llm_data_structure', '')}\n{row.get('llm_algorithm', '')}"
    in_trusted = _contains_any(trusted, aliases)
    in_tags = _contains_any(row.get("tags", ""), aliases)
    in_structured = _contains_any(weak, aliases)
    return in_trusted, in_tags, in_structured


def find_risky_structured(
    db_path: Path,
    term: str | None = None,
    limit: int = 1000,
) -> list[dict]:
    """
    Return problems where a data-structure term appears only in weak fields.

    Weak fields are tags and previously generated llm_* fields. Trusted fields
    are title and original statement content.
    """
    terms = [term] if term else sorted(DATA_STRUCTURE_TERMS)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, source, source_id, title, content, tags,
                  llm_algorithm, llm_data_structure, llm_core_operation
           FROM problems
           WHERE content != ''
           ORDER BY id"""
    ).fetchall()
    conn.close()

    risky = []
    for row in rows:
        item = dict(row)
        matched_terms = []
        for t in terms:
            in_trusted, in_tags, in_structured = _evidence(item, t)
            if not in_trusted and (in_tags or in_structured):
                matched_terms.append(t)
        if matched_terms:
            item["risky_terms"] = matched_terms
            risky.append(item)
            if len(risky) >= limit:
                break
    return risky


def print_risky_structured(db_path: Path, term: str | None = None, limit: int = 100) -> list[dict]:
    """Print a compact audit table and return risky rows."""
    risky = find_risky_structured(db_path, term=term, limit=limit)
    label = term or "all data-structure terms"
    print(f"\n🔎 Structured audit: {label}")
    print(f"{'ID':<8} {'Source':<12} {'SourceID':<12} {'RiskTerms':<20} {'Title'}")
    print("-" * 92)
    for row in risky:
        print(
            f"{row.get('id', ''):<8} "
            f"{row.get('source', ''):<12} "
            f"{row.get('source_id', ''):<12} "
            f"{','.join(row.get('risky_terms', []))[:18]:<20} "
            f"{row.get('title', '')[:36]}"
        )
    print(f"\nTotal shown: {len(risky)}")
    return risky
