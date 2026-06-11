"""Allow running as: python -m problem_db [crawl|import|enrich|enrich_luogu|preprocess|preprocess_risky|audit_structured|build|build_fts|search]"""
from problem_db import (
    cmd_crawl, cmd_enrich, cmd_enrich_luogu, cmd_preprocess,
    cmd_build_index, cmd_build_fts, cmd_search, cmd_import,
    cmd_audit_structured, cmd_preprocess_risky,
)
import sys

if len(sys.argv) < 2:
    print("Usage: python -m problem_db [crawl|import|enrich|enrich_luogu|preprocess|preprocess_risky|audit_structured|build|build_fts|search] [args]")
    sys.exit(1)

cmd = sys.argv[1]
if cmd == "crawl":
    cmd_crawl()
elif cmd == "import":
    source = sys.argv[2] if len(sys.argv) > 2 else "codeforces"
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    cmd_import(source, count)
elif cmd == "enrich":
    source = sys.argv[2] if len(sys.argv) > 2 else "codeforces"
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 5
    cmd_enrich(source, count, workers)
elif cmd == "enrich_luogu":
    max_problems = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    delay = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    cmd_enrich_luogu(max_problems, workers, delay)
elif cmd == "preprocess":
    args = sys.argv[2:]
    fast = "--fast" in args or "-f" in args
    force = "--force" in args
    for flag in ("--fast", "-f", "--force"):
        while flag in args:
            args.remove(flag)
    model = None
    if "--model" in args:
        i = args.index("--model")
        if i + 1 < len(args):
            model = args[i + 1]
            del args[i:i + 2]
    max_problems = int(args[0]) if len(args) > 0 else 0
    provider = args[1] if len(args) > 1 else "deepseek"
    delay = float(args[2]) if len(args) > 2 else 1.0
    cmd_preprocess(max_problems, provider, delay, fast, force, model)
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
elif cmd == "build":
    model = sys.argv[2] if len(sys.argv) > 2 else "mini"
    cmd_build_index(model)
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
