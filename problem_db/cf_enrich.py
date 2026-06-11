"""
Enrich Codeforces problems with full descriptions from problem pages.
Multi-threaded with rate limiting.
"""
import re
import sqlite3
import time
import random
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def extract_description(html: str) -> str:
    """Extract problem description from CF HTML page."""
    # Try to get the problem statement section
    match = re.search(
        r'<div class="problem-statement">(.*?)(?:<div class="input-specification">|<div class="sample-tests">)',
        html, re.DOTALL
    )
    if not match:
        # Fallback: try broader match
        match = re.search(
            r'<div class="problem-statement">(.*?)<div class="sample-tests">',
            html, re.DOTALL
        )
    if not match:
        return ""

    desc_html = match.group(1)

    # Remove script/style tags
    desc_html = re.sub(r'<script[^>]*>.*?</script>', '', desc_html, flags=re.DOTALL)
    desc_html = re.sub(r'<style[^>]*>.*?</style>', '', desc_html, flags=re.DOTALL)

    # Convert common HTML to text
    desc_html = re.sub(r'<br\s*/?>', '\n', desc_html)
    desc_html = re.sub(r'<p[^>]*>', '\n', desc_html)
    desc_html = re.sub(r'</p>', '\n', desc_html)
    desc_html = re.sub(r'<li[^>]*>', '\n- ', desc_html)
    desc_html = re.sub(r'<h[1-6][^>]*>', '\n## ', desc_html)

    # Remove all remaining HTML tags
    desc_text = re.sub(r'<[^>]+>', '', desc_html)

    # Clean up whitespace
    desc_text = re.sub(r'[ \t]+', ' ', desc_text)
    desc_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', desc_text)
    desc_text = desc_text.strip()

    return desc_text[:2000]  # Limit to 2000 chars


def fetch_problem_description(contest_id: str, index: str) -> str:
    """Fetch problem description from Codeforces."""
    url = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"
    req = urllib.request.Request(url, headers={
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        return extract_description(html)
    except Exception as e:
        return ""


def enrich_cf_problems(db_path: Path, batch_size: int = 100, max_problems: int = 0, workers: int = 5):
    """Enrich CF problems with full descriptions. Multi-threaded with rate limiting."""
    # Use single connection with check_same_thread=False for thread safety
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn_lock = threading.Lock()

    # Find problems without enriched content
    rows = conn.execute(
        "SELECT id, source_id, title FROM problems WHERE source = 'codeforces' "
        "AND (content NOT LIKE '%Theatre Square%' AND LENGTH(content) < 300) "
    ).fetchall()

    # Random shuffle to avoid pattern detection
    random.shuffle(rows)

    if max_problems > 0:
        rows = rows[:max_problems]

    print(f"📡 Enriching {len(rows)} CF problems with full descriptions ({workers} workers)...")
    print(f"   Rate limit: 1-3 seconds between requests per worker")

    enriched = 0
    failed = 0
    start = time.time()
    counter_lock = threading.Lock()
    counters = {"enriched": 0, "failed": 0}

    def process_one(item):
        db_id, source_id, title = item
        match = re.match(r'(\d+)([A-Z]\d*)', source_id)
        if not match:
            return None

        contest_id, index = match.group(1), match.group(2)

        # Rate limit: 1-3 seconds random delay
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

        desc = fetch_problem_description(contest_id, index)

        if desc and len(desc) > 50:
            new_content = f"Problem {source_id}: {title}\n\n{desc}"
            with conn_lock:
                conn.execute(
                    "UPDATE problems SET content = ? WHERE id = ?",
                    (new_content[:3000], db_id)
                )
            return ("enriched", source_id)
        else:
            return ("failed", source_id)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_one, item): item for item in rows}
        done_count = 0

        for future in as_completed(futures):
            done_count += 1
            result = future.result()
            if result:
                with counter_lock:
                    if result[0] == "enriched":
                        counters["enriched"] += 1
                    else:
                        counters["failed"] += 1

            # Progress every 50
            if done_count % 50 == 0:
                elapsed = time.time() - start
                rate = done_count / elapsed * 60
                eta = (len(rows) - done_count) / rate if rate > 0 else 0
                print(f"  ... {done_count}/{len(rows)} | enriched: {counters['enriched']} | "
                      f"failed: {counters['failed']} | {rate:.0f}/min | ETA: {eta:.0f}min")
                with conn_lock:
                    conn.commit()

    with conn_lock:
        conn.commit()
    conn.close()

    elapsed = time.time() - start
    print(f"\n✅ Done: {counters['enriched']} enriched, {counters['failed']} failed, {elapsed:.0f}s total")


if __name__ == "__main__":
    import sys
    db_path = Path("problem_data/problems.db")
    max_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    enrich_cf_problems(db_path, max_problems=max_problems)
