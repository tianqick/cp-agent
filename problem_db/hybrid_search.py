"""
Hybrid retrieval for competitive-programming problem search.

The vector index is useful for broad semantic similarity, but it often
collapses domain terms such as "线段树" into the broader word "树".  This
module combines vector recall with keyword/FTS recall and domain-term rerank.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path


TERM_ALIASES: dict[str, list[str]] = {
    "线段树": ["线段树", "segment tree", "segtree"],
    "树状数组": ["树状数组", "fenwick", "binary indexed tree", "bit"],
    "并查集": ["并查集", "dsu", "union find", "disjoint set union"],
    "主席树": ["主席树", "可持久化线段树", "persistent segment tree"],
    "树链剖分": ["树链剖分", "heavy light decomposition", "hld"],
    "最短路": ["最短路", "dijkstra", "spfa", "floyd", "shortest path"],
    "网络流": ["网络流", "最大流", "max flow", "dinic"],
    "二分图匹配": ["二分图匹配", "bipartite matching", "hopcroft", "kuhn"],
    "动态规划": ["动态规划", "dp", "dynamic programming"],
    "背包": ["背包", "knapsack"],
    "单调队列": ["单调队列", "monotonic queue"],
    "单调栈": ["单调栈", "monotonic stack"],
    "字典树": ["字典树", "trie"],
    "后缀数组": ["后缀数组", "suffix array"],
    "后缀自动机": ["后缀自动机", "sam", "suffix automaton"],
    "kmp": ["kmp"],
    "gcd": ["gcd", "最大公约数", "gcd"],
    "区间查询": ["区间查询", "range query", "区间"],
}

DATA_STRUCTURE_TERMS = {
    "线段树",
    "树状数组",
    "并查集",
    "主席树",
    "树链剖分",
    "单调队列",
    "单调栈",
    "字典树",
    "后缀数组",
    "后缀自动机",
}

FTS_COLUMNS = (
    "title",
    "content",
    "tags",
    "llm_algorithm",
    "llm_data_structure",
    "llm_core_operation",
    "llm_standardized",
)


def ensure_fts_index(db_path: Path, rebuild: bool = False) -> None:
    """Create and populate the FTS5 table used by keyword recall."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS problems_fts USING fts5(
                title,
                content,
                tags,
                llm_algorithm,
                llm_data_structure,
                llm_core_operation,
                llm_standardized
            )
            """
        )

        problem_count = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
        fts_count = conn.execute("SELECT COUNT(*) FROM problems_fts").fetchone()[0]

        if rebuild or fts_count != problem_count:
            conn.execute("DELETE FROM problems_fts")
            conn.execute(
                """
                INSERT INTO problems_fts(
                    rowid,
                    title,
                    content,
                    tags,
                    llm_algorithm,
                    llm_data_structure,
                    llm_core_operation,
                    llm_standardized
                )
                SELECT
                    id,
                    COALESCE(title, ''),
                    COALESCE(content, ''),
                    COALESCE(tags, ''),
                    COALESCE(llm_algorithm, ''),
                    COALESCE(llm_data_structure, ''),
                    COALESCE(llm_core_operation, ''),
                    COALESCE(llm_standardized, '')
                FROM problems
                """
            )
        conn.commit()
    finally:
        conn.close()


def extract_terms(query: str) -> list[str]:
    """Return canonical domain terms explicitly present in the query."""
    q = query.lower()
    found = []
    for canonical, aliases in TERM_ALIASES.items():
        for alias in aliases:
            if alias.lower() in q:
                found.append(canonical)
                break
    return found


def expand_query_terms(query: str, required_terms: list[str]) -> list[str]:
    """Build exact keyword candidates for LIKE recall and FTS matching."""
    terms: list[str] = []
    for term in required_terms:
        terms.extend(TERM_ALIASES.get(term, [term]))

    for token in re.split(r"[\s,，;；]+", query.strip()):
        token = token.strip()
        if len(token) >= 2:
            terms.append(token)

    deduped = []
    seen = set()
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(term)
    return deduped


def _fetch_problem(conn: sqlite3.Connection, problem_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM problems WHERE id = ?", (problem_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def _text_contains(text: object, aliases: list[str]) -> bool:
    if text is None:
        return False
    t = str(text).lower()
    return any(alias.lower() in t for alias in aliases)


def _combined_text(problem: dict) -> str:
    return "\n".join(str(problem.get(col, "") or "") for col in FTS_COLUMNS)


def term_coverage(problem: dict, required_terms: list[str]) -> int:
    """Count how many canonical query terms are explicitly present."""
    if not required_terms:
        return 0
    combined = _combined_text(problem)
    return sum(
        1
        for term in required_terms
        if _text_contains(combined, TERM_ALIASES.get(term, [term]))
    )


def term_match_strength(problem: dict, required_terms: list[str]) -> float:
    """
    Weighted domain-term evidence by field reliability.

    Title and original statement text are much more trustworthy than scraped
    tags/LLM-preprocessed fields in this dataset, especially for Luogu.
    """
    strength = 0.0
    for term in required_terms:
        aliases = TERM_ALIASES.get(term, [term])
        best = 0.0
        if _text_contains(problem.get("title"), aliases):
            best = max(best, 3.0)
        if _text_contains(problem.get("content"), aliases):
            best = max(best, 2.2)
        if _text_contains(problem.get("llm_data_structure"), aliases):
            best = max(best, 1.2)
        if _text_contains(problem.get("llm_algorithm"), aliases):
            best = max(best, 0.9)
        if _text_contains(problem.get("tags"), aliases):
            best = max(best, 0.7)
        if _text_contains(problem.get("llm_standardized"), aliases):
            best = max(best, 0.5)
        strength += best
    return strength


def missing_required_structures(problem: dict, required_terms: list[str]) -> list[str]:
    """Data-structure terms in the query are treated as hard-ish constraints."""
    missing = []
    combined = _combined_text(problem)
    for term in required_terms:
        if term not in DATA_STRUCTURE_TERMS:
            continue
        if not _text_contains(combined, TERM_ALIASES.get(term, [term])):
            missing.append(term)
    return missing


def keyword_search(db_path: Path, query: str, top_k: int = 100) -> list[dict]:
    """
    Keyword recall using both FTS and exact LIKE aliases.

    FTS5 is fast for English/tags, while LIKE is intentionally kept for Chinese
    algorithm names because SQLite FTS tokenization is not reliable enough for
    terms such as "线段树".
    """
    ensure_fts_index(db_path)
    required_terms = extract_terms(query)
    exact_terms = expand_query_terms(query, required_terms)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    merged: dict[int, dict] = {}

    try:
        fts_query = " OR ".join(f'"{term.replace(chr(34), " ")}"' for term in exact_terms[:12])
        if fts_query:
            try:
                rows = conn.execute(
                    """
                    SELECT p.*, bm25(problems_fts) AS bm25_score
                    FROM problems_fts
                    JOIN problems p ON p.id = problems_fts.rowid
                    WHERE problems_fts MATCH ?
                    ORDER BY bm25_score
                    LIMIT ?
                    """,
                    (fts_query, top_k),
                ).fetchall()
                for rank, row in enumerate(rows, 1):
                    item = dict(row)
                    item["keyword_rank"] = rank
                    item["bm25_score"] = float(item.pop("bm25_score", 0.0))
                    merged[item["id"]] = item
            except sqlite3.OperationalError:
                # Bad tokenizer/query combinations should not kill search.
                pass

        for term in exact_terms[:20]:
            like = f"%{term}%"
            where = " OR ".join(f"COALESCE({col}, '') LIKE ?" for col in FTS_COLUMNS)
            rows = conn.execute(
                f"""
                SELECT * FROM problems
                WHERE {where}
                LIMIT ?
                """,
                (*(like for _ in FTS_COLUMNS), top_k),
            ).fetchall()

            for row in rows:
                item = dict(row)
                text = _combined_text(item).lower()
                exact_hits = sum(1 for t in exact_terms if t.lower() in text)
                if exact_hits <= 0:
                    continue
                existing = merged.get(item["id"], item)
                existing["exact_hits"] = max(existing.get("exact_hits", 0), exact_hits)
                merged[item["id"]] = existing

    finally:
        conn.close()

    results = list(merged.values())
    for result in results:
        result["term_coverage"] = term_coverage(result, required_terms)
        result["term_strength"] = term_match_strength(result, required_terms)
    results.sort(
        key=lambda r: (
            r.get("term_coverage", 0),
            r.get("term_strength", 0.0),
            r.get("exact_hits", 0),
            -r.get("keyword_rank", 10**9),
        ),
        reverse=True,
    )
    for rank, result in enumerate(results[:top_k], 1):
        result["keyword_rank"] = min(result.get("keyword_rank", rank), rank)
    return results[:top_k]


def structured_bonus(problem: dict, required_terms: list[str]) -> float:
    """Score explicit matches in curated/structured fields."""
    if not required_terms:
        return 0.0

    bonus = 0.0
    combined = _combined_text(problem)
    for term in required_terms:
        aliases = TERM_ALIASES.get(term, [term])

        if _text_contains(problem.get("title"), aliases):
            bonus += 2.0
        if _text_contains(problem.get("content"), aliases):
            bonus += 1.2
        if _text_contains(problem.get("llm_data_structure"), aliases):
            bonus += 0.8
        if _text_contains(problem.get("tags"), aliases):
            bonus += 0.5
        if _text_contains(problem.get("llm_algorithm"), aliases):
            bonus += 0.5
        if _text_contains(problem.get("llm_standardized"), aliases):
            bonus += 0.3

        # Protect specific tree terms from being swallowed by generic trees.
        if term == "线段树":
            data_structure = str(problem.get("llm_data_structure", "") or "")
            tags = str(problem.get("tags", "") or "")
            if "树" in data_structure and "线段树" not in data_structure and "线段树" not in tags:
                bonus -= 1.2
        if term == "树状数组":
            combined_lower = combined.lower()
            if "数组" in combined_lower and "树状数组" not in combined_lower and "fenwick" not in combined_lower:
                bonus -= 0.8

    return bonus


def _rrf(rank: int | None, k: int = 60) -> float:
    if not rank:
        return 0.0
    return 1.0 / (k + rank)


def hybrid_search(
    db_path: Path,
    index_path: Path,
    query: str,
    top_k: int = 10,
    model_key: str = "mini",
    vector_limit: int = 100,
    keyword_limit: int = 100,
) -> list[dict]:
    """Search by vector + keyword recall, then rerank with domain terms."""
    from .embedder import get_embedder
    from .index import ProblemIndex

    required_terms = extract_terms(query)
    merged: dict[int, dict] = {}

    try:
        embedder = get_embedder(model_key)
        query_vec = embedder.encode_single(query)
        idx = ProblemIndex(db_path, index_path)
        vector_results = idx.search_and_resolve(query_vec, vector_limit)
    except Exception as e:
        print(f"⚠️ Vector recall unavailable, falling back to keyword search: {e}")
        vector_results = []

    for rank, item in enumerate(vector_results, 1):
        problem_id = item.get("id") or item.get("problem_db_id")
        if not problem_id:
            continue
        item["vector_rank"] = rank
        item["vector_score"] = float(item.get("score", 0.0))
        merged[int(problem_id)] = item

    for rank, item in enumerate(keyword_search(db_path, query, keyword_limit), 1):
        problem_id = int(item["id"])
        existing = merged.get(problem_id)
        if existing is None:
            existing = item
            existing["vector_score"] = 0.0
        existing["keyword_rank"] = min(existing.get("keyword_rank", rank), rank)
        existing["exact_hits"] = max(existing.get("exact_hits", 0), item.get("exact_hits", 0))
        existing["term_coverage"] = max(existing.get("term_coverage", 0), item.get("term_coverage", 0))
        existing["term_strength"] = max(existing.get("term_strength", 0.0), item.get("term_strength", 0.0))
        merged[problem_id] = existing

    scored = []
    for item in merged.values():
        bonus = structured_bonus(item, required_terms)
        exact_hits = item.get("exact_hits", 0)
        coverage = item.get("term_coverage", term_coverage(item, required_terms))
        strength = item.get("term_strength", term_match_strength(item, required_terms))
        missing_structures = missing_required_structures(item, required_terms)
        final_score = (
            0.35 * _rrf(item.get("vector_rank")) +
            0.45 * _rrf(item.get("keyword_rank")) +
            0.10 * coverage +
            0.06 * strength +
            0.04 * exact_hits +
            0.08 * bonus -
            0.80 * len(missing_structures)
        )
        item["term_bonus"] = bonus
        item["term_coverage"] = coverage
        item["term_strength"] = strength
        item["missing_structure_terms"] = missing_structures
        item["matched_terms"] = required_terms
        item["final_score"] = final_score
        scored.append(item)

    scored.sort(key=lambda r: r["final_score"], reverse=True)
    for rank, item in enumerate(scored[:top_k], 1):
        item["rank"] = rank
    return scored[:top_k]


def vector_search(db_path: Path, index_path: Path, query: str, top_k: int = 10, model_key: str = "mini") -> list[dict]:
    """Original vector-only search, kept for comparison."""
    from .embedder import get_embedder
    from .index import ProblemIndex

    embedder = get_embedder(model_key)
    query_vec = embedder.encode_single(query)
    idx = ProblemIndex(db_path, index_path)
    results = idx.search_and_resolve(query_vec, top_k)
    for result in results:
        result["vector_score"] = float(result.get("score", 0.0))
    return results
