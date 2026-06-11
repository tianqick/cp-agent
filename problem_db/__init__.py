"""
Problem Database: crawl, import, enrich, build index, and search for duplicate problems.

Usage:
    python -m problem_db crawl [source]            # Crawl CF API
    python -m problem_db import [codeforces|luogu]  # Import from datasets
    python -m problem_db enrich [source] [count] [workers]  # Enrich CF descriptions
    python -m problem_db build                      # Build FAISS index
    python -m problem_db search "线段树 区间GCD"     # Search similar problems
"""
from pathlib import Path

DB_DIR = Path(__file__).parent.parent / "problem_data"
DB_PATH = DB_DIR / "problems.db"
INDEX_PATH = DB_DIR / "problems.faiss"


def ensure_dirs():
    DB_DIR.mkdir(parents=True, exist_ok=True)


def cmd_crawl(counts: dict = None):
    """Crawl all platforms."""
    from .crawler import crawl_all
    ensure_dirs()
    crawl_all(DB_PATH, counts)


def cmd_build_index(model_key: str = "mini"):
    """Build FAISS index from crawled data."""
    from .embedder import get_embedder
    from .index import ProblemIndex
    from .llm_preprocessor import VECTOR_TEXT_VERSION, get_standardized_text
    import sqlite3

    ensure_dirs()

    # Load problems from DB
    conn = sqlite3.connect(str(DB_PATH))

    # Check if LLM preprocessing columns exist
    cursor = conn.execute("PRAGMA table_info(problems)")
    columns = [row[1] for row in cursor.fetchall()]

    if "llm_standardized" in columns:
        # Use LLM-preprocessed text if available
        rows = conn.execute(
            """SELECT id, title, content, tags, difficulty,
                      llm_standardized, llm_algorithm, llm_data_structure,
                      llm_core_operation, llm_difficulty_level
               FROM problems"""
        ).fetchall()
        print("✓ Using title/content-first text with LLM fields as references")
    else:
        # Fallback to basic text
        rows = conn.execute("SELECT id, title, content, tags FROM problems").fetchall()
        # Convert to same format for processing
        rows = [(r[0], r[1], r[2], r[3], "", "", "", "", "") for r in rows]
        print("⚠️ No LLM preprocessing found, using basic text")

    conn.close()

    if not rows:
        print("❌ No problems in database. Run 'crawl' first.")
        return

    print(f"📊 {len(rows)} problems to index")

    # Prepare texts using standardized format
    problem_ids = [r[0] for r in rows]
    texts = [get_standardized_text(r) for r in rows]

    # Generate embeddings
    embedder = get_embedder(model_key)
    vectors = embedder.encode(texts, batch_size=64)

    # Build FAISS index
    idx = ProblemIndex(DB_PATH, INDEX_PATH)
    idx.build(vectors, problem_ids)
    idx.save({
        "model_key": model_key,
        "model_name": embedder.model_name,
        "text_version": VECTOR_TEXT_VERSION,
        "problem_count": len(problem_ids),
    })

    print(f"✅ Index built and saved")


def cmd_enrich(source: str = "codeforces", count: int = 0, workers: int = 5):
    """Enrich problems with full descriptions."""
    if source not in ("cf", "codeforces"):
        print(f"Only 'cf'/'codeforces' enrichment supported, got: {source}")
        return 0
    from .cf_enrich import enrich_cf_problems
    ensure_dirs()
    return enrich_cf_problems(DB_PATH, max_problems=count, workers=workers)


def cmd_import(source: str = "codeforces", count: int = 0):
    """Import problems from external datasets."""
    ensure_dirs()
    if source in ("cf", "codeforces"):
        from .import_deepmind import import_deepmind_cf
        return import_deepmind_cf(DB_PATH)
    elif source in ("luogu", "lg"):
        from .import_luogu import import_luogu_all
        return import_luogu_all(DB_PATH)
    else:
        print(f"Unknown import source: {source}")
        return 0


def cmd_enrich_luogu(max_problems: int = 0, workers: int = 3, delay: float = 2.0):
    """Enrich Luogu problems with full descriptions from luogu.com.cn."""
    from .luogu_enrich import enrich_luogu_problems
    ensure_dirs()
    return enrich_luogu_problems(DB_PATH, max_problems=max_problems,
                                 workers=workers, delay=delay)


def cmd_preprocess(max_problems: int = 0, provider: str = "deepseek",
                   delay: float = 1.0, fast: bool = False,
                   force: bool = False, model: str | None = None):
    """Preprocess problems for better vectorization."""
    ensure_dirs()
    if fast:
        from .fast_preprocessor import preprocess_problems_batch_fast
        return preprocess_problems_batch_fast(DB_PATH, max_problems=max_problems,
                                              force=force)
    else:
        from .llm_preprocessor import preprocess_problems_batch
        return preprocess_problems_batch(DB_PATH, max_problems=max_problems,
                                         provider=provider, delay=delay,
                                         force=force, model=model)


def cmd_audit_structured(term: str | None = None, limit: int = 100):
    """Audit likely false-positive structured fields."""
    from .structured_audit import print_risky_structured

    ensure_dirs()
    return print_risky_structured(DB_PATH, term=term, limit=limit)


def cmd_preprocess_risky(provider: str = "deepseek", delay: float = 1.0,
                         limit: int = 500, term: str | None = None,
                         model: str | None = None):
    """Use LLM preprocessing only for high-risk structured-field rows."""
    from .structured_audit import find_risky_structured
    from .llm_preprocessor import preprocess_problems_batch

    ensure_dirs()
    risky = find_risky_structured(DB_PATH, term=term, limit=limit)
    ids = [int(row["id"]) for row in risky]
    if not ids:
        print("✓ No risky structured rows found")
        return 0
    print(f"📊 {len(ids)} risky rows selected for LLM re-labeling")
    return preprocess_problems_batch(
        DB_PATH,
        provider=provider,
        delay=delay,
        problem_ids=ids,
        model=model,
    )


def cmd_build_fts(rebuild: bool = True):
    """Build or rebuild the SQLite FTS index used by hybrid search."""
    from .hybrid_search import ensure_fts_index

    ensure_dirs()
    ensure_fts_index(DB_PATH, rebuild=rebuild)
    print("✅ FTS index built")


def cmd_search(query: str, top_k: int = 10, model_key: str = "mini",
               vector_only: bool = False):
    """Search for similar problems. Defaults to hybrid retrieval."""
    from .hybrid_search import hybrid_search, vector_search

    ensure_dirs()

    if vector_only:
        results = vector_search(DB_PATH, INDEX_PATH, query, top_k, model_key)
        print(f"\n🔍 Vector Search: \"{query}\"")
        print(f"{'Rank':<6} {'Vec':<8} {'Source':<12} {'ID':<12} {'Title'}")
        print("-" * 76)
        for r in results:
            print(f"{r.get('rank', ''):<6} {r.get('vector_score', 0):.4f}   "
                  f"{r.get('source', ''):<12} {r.get('source_id', ''):<12} "
                  f"{r.get('title', '')[:44]}")
        return results

    results = hybrid_search(DB_PATH, INDEX_PATH, query, top_k, model_key)

    print(f"\n🔍 Hybrid Search: \"{query}\"")
    if results and results[0].get("matched_terms"):
        print(f"Matched terms: {', '.join(results[0]['matched_terms'])}")
    print(f"{'Rank':<6} {'Final':<8} {'Vec':<8} {'KRank':<7} {'Cov':<4} {'Str':<5} {'Hit':<4} "
          f"{'Bonus':<7} {'Source':<12} {'ID':<12} {'Title'}")
    print("-" * 119)
    for r in results:
        print(f"{r.get('rank', ''):<6} {r.get('final_score', 0):.4f}   "
              f"{r.get('vector_score', 0):.4f}   "
              f"{str(r.get('keyword_rank', '-')):<7} "
              f"{r.get('term_coverage', 0):<4} "
              f"{r.get('term_strength', 0):<5.1f} "
              f"{r.get('exact_hits', 0):<4} "
              f"{r.get('term_bonus', 0):<7.2f} "
              f"{r.get('source', ''):<12} {r.get('source_id', ''):<12} "
              f"{r.get('title', '')[:36]}")

    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m problem_db [crawl|build|search] [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "crawl":
        cmd_crawl()
    elif cmd == "enrich":
        source = sys.argv[2] if len(sys.argv) > 2 else "cf"
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 500
        cmd_enrich(source, count)
    elif cmd == "build":
        model = sys.argv[2] if len(sys.argv) > 2 else "mini"
        cmd_build_index(model)
    elif cmd == "audit_structured":
        args = sys.argv[2:]
        term = None
        if "--term" in args:
            i = args.index("--term")
            if i + 1 < len(args):
                term = args[i + 1]
                del args[i:i + 2]
        limit = 100
        if "--limit" in args:
            i = args.index("--limit")
            if i + 1 < len(args):
                limit = int(args[i + 1])
                del args[i:i + 2]
        cmd_audit_structured(term=term, limit=limit)
    elif cmd == "preprocess_risky":
        args = sys.argv[2:]
        model = None
        if "--model" in args:
            i = args.index("--model")
            if i + 1 < len(args):
                model = args[i + 1]
                del args[i:i + 2]
        term = None
        if "--term" in args:
            i = args.index("--term")
            if i + 1 < len(args):
                term = args[i + 1]
                del args[i:i + 2]
        limit = 500
        if "--limit" in args:
            i = args.index("--limit")
            if i + 1 < len(args):
                limit = int(args[i + 1])
                del args[i:i + 2]
        provider = args[0] if len(args) > 0 else "deepseek"
        delay = float(args[1]) if len(args) > 1 else 1.0
        cmd_preprocess_risky(provider=provider, delay=delay, limit=limit,
                             term=term, model=model)
    elif cmd == "build_fts":
        rebuild = "--no-rebuild" not in sys.argv
        cmd_build_fts(rebuild=rebuild)
    elif cmd == "search":
        args = sys.argv[2:]
        vector_only = "--vector-only" in args
        if vector_only:
            args.remove("--vector-only")
        model = "mini"
        if "--model" in args:
            i = args.index("--model")
            if i + 1 < len(args):
                model = args[i + 1]
                del args[i:i + 2]
        top_k = 10
        if "--top-k" in args:
            i = args.index("--top-k")
            if i + 1 < len(args):
                top_k = int(args[i + 1])
                del args[i:i + 2]
        query = " ".join(args) if args else "动态规划"
        cmd_search(query, top_k=top_k, model_key=model, vector_only=vector_only)
    else:
        print(f"Unknown command: {cmd}")
