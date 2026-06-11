"""
Problem crawler with rate limiting for multiple OJ platforms.
Targets: Luogu, Nowcoder, Codeforces, AtCoder
"""
import json
import random
import sqlite3
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# ─── Rate limiter ────────────────────────────────────────────────────────────

class RateLimiter:
    """Rate limiter with random delay and exponential backoff."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0,
                 max_retries: int = 3, backoff_factor: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.last_request_time = 0

    def wait(self):
        """Wait for a random delay between requests."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def on_error(self, attempt: int):
        """Exponential backoff on error."""
        wait_time = self.backoff_factor ** attempt + random.uniform(1, 3)
        print(f"    ⏳ Backoff {wait_time:.1f}s (attempt {attempt + 1}/{self.max_retries})")
        time.sleep(wait_time)


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def fetch_url(url: str, rate_limiter: RateLimiter,
              headers: dict = None, timeout: int = 15) -> Optional[str]:
    """Fetch URL with rate limiting and retry logic."""
    for attempt in range(rate_limiter.max_retries):
        rate_limiter.wait()

        req_headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/json",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    ⚠ Rate limited (429) on {url}")
                rate_limiter.on_error(attempt)
                continue
            elif e.code == 404:
                return None
            else:
                print(f"    ⚠ HTTP {e.code} on {url}")
                if attempt < rate_limiter.max_retries - 1:
                    rate_limiter.on_error(attempt)
                continue
        except Exception as e:
            print(f"    ⚠ Error fetching {url}: {e}")
            if attempt < rate_limiter.max_retries - 1:
                rate_limiter.on_error(attempt)
            continue

    return None


# ─── Database ────────────────────────────────────────────────────────────────

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize SQLite database for problems."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            difficulty TEXT,
            tags TEXT,
            url TEXT,
            UNIQUE(source, source_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON problems(source)")
    conn.commit()
    return conn


def save_problem(conn: sqlite3.Connection, source: str, source_id: str,
                 title: str, content: str, difficulty: str = "",
                 tags: str = "", url: str = "") -> bool:
    """Save a problem to the database. Returns True if new, False if duplicate."""
    try:
        conn.execute(
            "INSERT INTO problems (source, source_id, title, content, difficulty, tags, url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (source, source_id, title, content[:2000], difficulty, tags, url)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


# ─── Codeforces crawler ─────────────────────────────────────────────────────

def crawl_codeforces(conn: sqlite3.Connection, count: int = 2000) -> int:
    """Crawl Codeforces problems via API. Returns number of new problems."""
    print("\n📡 Crawling Codeforces...")
    rl = RateLimiter(min_delay=3, max_delay=6)
    new_count = 0

    # Use Codeforces API (official, no ban risk)
    url = "https://codeforces.com/api/problemset.problems"
    print(f"  Fetching problem list from API...")
    data = fetch_url(url, rl)
    if not data:
        print("  ✗ Failed to fetch Codeforces API")
        return 0

    try:
        result = json.loads(data)
        problems = result.get("result", {}).get("problems", [])
        print(f"  Found {len(problems)} problems")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ✗ Parse error: {e}")
        return 0

    for p in problems[:count]:
        contest_id = p.get("contestId", "")
        index = p.get("index", "")
        source_id = f"{contest_id}{index}"
        title = p.get("name", "")
        tags = ", ".join(p.get("tags", []))
        rating = p.get("rating", "")
        difficulty = str(rating) if rating else ""
        url_str = f"https://codeforces.com/problemset/problem/{contest_id}/{index}"

        # Fetch problem page for description (only first 500 chars)
        desc = f"Problem {source_id}: {title}. Tags: {tags}. Rating: {difficulty}"

        if save_problem(conn, "codeforces", source_id, title, desc, difficulty, tags, url_str):
            new_count += 1
            if new_count % 50 == 0:
                print(f"  ... {new_count} new problems saved")

    print(f"  ✓ Codeforces: {new_count} new problems")
    return new_count


# ─── AtCoder crawler ────────────────────────────────────────────────────────

def crawl_atcoder(conn: sqlite3.Connection, count: int = 2000) -> int:
    """Crawl AtCoder problems. Returns number of new problems."""
    print("\n📡 Crawling AtCoder...")
    rl = RateLimiter(min_delay=3, max_delay=6)
    new_count = 0

    # AtCoder has a problems API
    for page in range(1, (count // 50) + 2):
        url = f"https://kenkoooo.com/atcoder/resources/problems.json"
        if page == 1:
            data = fetch_url(url, rl)
            if not data:
                print("  ✗ Failed to fetch AtCoder problems")
                return 0
            try:
                problems = json.loads(data)
                print(f"  Found {len(problems)} problems")
            except json.JSONDecodeError as e:
                print(f"  ✗ Parse error: {e}")
                return 0

            for p in problems[:count]:
                source_id = p.get("id", "")
                title = p.get("title", "")
                contest_id = p.get("contest_id", "")
                url_str = f"https://atcoder.jp/contests/{contest_id}/tasks/{source_id}"
                desc = f"AtCoder problem {source_id}: {title}"

                if save_problem(conn, "atcoder", source_id, title, desc, "", "", url_str):
                    new_count += 1
                    if new_count % 50 == 0:
                        print(f"  ... {new_count} new problems saved")
            break

    print(f"  ✓ AtCoder: {new_count} new problems")
    return new_count


# ─── Luogu crawler ──────────────────────────────────────────────────────────

def crawl_luogu(conn: sqlite3.Connection, count: int = 2000) -> int:
    """Crawl Luogu problems. Returns number of new problems."""
    print("\n📡 Crawling Luogu...")
    rl = RateLimiter(min_delay=4, max_delay=8)  # Luogu is stricter
    new_count = 0

    # Luogu API for problem list
    for page in range(1, min(count // 100 + 2, 20)):
        url = f"https://www.luogu.com.cn/problem/list?page={page}&_contentOnly=1"
        data = fetch_url(url, rl, headers={"Referer": "https://www.luogu.com.cn/"})
        if not data:
            print(f"  ✗ Failed to fetch page {page}")
            break

        try:
            result = json.loads(data)
            problems = result.get("currentData", {}).get("problems", {}).get("result", [])
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            print(f"  ✗ Parse error on page {page}: {e}")
            break

        if not problems:
            break

        for p in problems:
            pid = p.get("pid", "")
            title = p.get("title", "")
            difficulty = p.get("difficulty", 0)
            tags_list = p.get("tags", [])
            tags = ", ".join([t.get("name", "") for t in tags_list if isinstance(t, dict)])
            url_str = f"https://www.luogu.com.cn/problem/{pid}"
            desc = f"Luogu problem {pid}: {title}. Difficulty: {difficulty}. Tags: {tags}"

            if save_problem(conn, "luogu", pid, title, desc, str(difficulty), tags, url_str):
                new_count += 1

        print(f"  Page {page}: +{len(problems)} problems (total new: {new_count})")
        if new_count >= count:
            break

    print(f"  ✓ Luogu: {new_count} new problems")
    return new_count


# ─── Nowcoder crawler ───────────────────────────────────────────────────────

def crawl_nowcoder(conn: sqlite3.Connection, count: int = 2000) -> int:
    """Crawl Nowcoder (牛客) problems. Returns number of new problems."""
    print("\n📡 Crawling Nowcoder...")
    rl = RateLimiter(min_delay=4, max_delay=8)
    new_count = 0

    # Nowcoder practice problems API
    for page in range(1, min(count // 20 + 2, 100)):
        url = f"https://ac.nowcoder.com/acm/contest/realtime?pageSize=20&page={page}"
        data = fetch_url(url, rl)
        if not data:
            print(f"  ✗ Failed to fetch page {page}")
            break

        # Nowcoder uses HTML, parse basic info
        try:
            import re
            # Extract problem links and titles from HTML
            matches = re.findall(r'/acm/problem/(\d+)"[^>]*>([^<]+)', data)
            if not matches:
                # Try alternative pattern
                matches = re.findall(r'problemId=(\d+)[^>]*>([^<]+)', data)
        except Exception:
            matches = []

        if not matches and page > 3:
            break

        for pid, title in matches[:20]:
            title = title.strip()
            if not title:
                continue
            url_str = f"https://ac.nowcoder.com/acm/problem/{pid}"
            desc = f"Nowcoder problem {pid}: {title}"

            if save_problem(conn, "nowcoder", pid, title, desc, "", "", url_str):
                new_count += 1

        if new_count >= count:
            break

    print(f"  ✓ Nowcoder: {new_count} new problems")
    return new_count


# ─── Main entry ──────────────────────────────────────────────────────────────

def crawl_all(db_path: Path, counts: dict = None) -> dict:
    """Crawl all platforms and save to database. Returns summary."""
    if counts is None:
        counts = {
            "codeforces": 3000,
            "atcoder": 2000,
            "luogu": 2000,
            "nowcoder": 1000,
        }

    conn = init_db(db_path)
    results = {}

    print(f"🗂  Database: {db_path}")

    for platform, count in counts.items():
        crawler_fn = {
            "codeforces": crawl_codeforces,
            "atcoder": crawl_atcoder,
            "luogu": crawl_luogu,
            "nowcoder": crawl_nowcoder,
        }.get(platform)

        if crawler_fn:
            try:
                results[platform] = crawler_fn(conn, count)
            except Exception as e:
                print(f"  ✗ {platform} failed: {e}")
                results[platform] = 0

    # Show summary
    total = conn.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
    print(f"\n📊 Total problems in database: {total}")
    for source, count in conn.execute(
        "SELECT source, COUNT(*) FROM problems GROUP BY source"
    ).fetchall():
        print(f"  {source}: {count}")

    conn.close()
    return results
