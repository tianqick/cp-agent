"""
Import Luogu problems from GitHub repositories.
1. Metadata from Molmin/luoguProblems-datas (difficulty, tags, stats)
2. Problem descriptions from OldAntique110/Luogu-Problems (Markdown)
"""
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path


def download_json(url: str) -> dict:
    """Download JSON from URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_text(url: str) -> str:
    """Download text from URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def import_luogu_metadata(db_path: Path):
    """Import Luogu problem metadata (difficulty, tags, stats)."""
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

    # Tag ID to name mapping (common Luogu tags)
    TAG_MAP = {
        1: "模拟", 2: "字符串", 3: "动态规划", 4: "贪心", 5: "数学",
        6: "数据结构", 7: "图论", 8: "搜索", 9: "二分", 10: "分治",
        11: "构造", 12: "博弈", 13: "几何", 14: "数论", 15: "组合数学",
        16: "概率", 17: "背包", 18: "树形DP", 19: "状压DP", 20: "区间DP",
        21: "数位DP", 22: "插头DP", 23: "CDQ分治", 24: "整体二分", 25: "莫队",
        26: "树链剖分", 27: "LCT", 28: "线段树", 29: "树状数组", 30: "平衡树",
        31: "堆", 32: "并查集", 33: "字典树", 34: "AC自动机", 35: "后缀数组",
        36: "后缀自动机", 37: "KMP", 38: "哈希", 39: "最短路", 40: "最小生成树",
        41: "网络流", 42: "二分图", 43: "强连通分量", 44: "拓扑排序", 45: "欧拉回路",
        46: "双连通分量", 47: "2-SAT", 48: "矩阵快速幂", 49: "高斯消元", 50: "FFT",
        51: "容斥", 52: "莫比乌斯反演", 53: "中国剩余定理", 54: "扩展欧几里得",
        55: "逆元", 56: "卡特兰数", 57: "斯特林数", 58: "Burnside引理",
        59: "Pollard-Rho", 60: "Miller-Rabin", 61: "BSGS", 62: "Pell方程",
        63: "Lucas定理", 64: "原根", 65: "二次剩余", 66: "高次剩余",
        82: "记忆化搜索", 83: "递归", 84: "递推", 85: "分块", 86: "树分治",
        87: "点分治", 88: "边分治", 89: "虚树", 90: "树上差分", 91: "树上倍增",
        92: "LCA", 93: "树的直径", 94: "树的重心", 95: "DFS序", 96: "欧拉序",
        97: "括号序", 98: "轻重链剖分", 99: "长链剖分", 100: "树上启发式合并",
        101: "可持久化线段树", 102: "可持久化字典树", 103: "可持久化并查集",
        104: "可持久化平衡树", 105: "可持久化数组", 106: "可持久化01Trie",
        107: "可持久化块状链表", 108: "高精度", 109: "模拟退火", 110: "随机化",
        111: "暴力枚举", 112: "打表", 113: "思维", 114: "交互题", 115: "提交答案题",
        116: "通信题", 117: "论文题", 118: "CF套题", 119: "AT套题", 120: "LG套题",
        121: "蓝桥杯", 122: "CSP", 123: "NOIP", 124: "省选", 125: "NOI",
        126: "CTSC", 127: "APIO", 128: "IOI", 129: "JOI", 130: "USACO",
        201: "链表", 202: "栈", 203: "队列", 204: "动态规划优化",
        205: "单调栈", 206: "单调队列", 207: "斜率优化", 208: "四边形不等式",
        209: "决策单调性", 210: "CDQ优化DP", 211: "WQS二分",
    }

    print("📦 Downloading Luogu metadata...")
    files = {
        "P.json": "luogu",
        "SP.json": "luogu",
    }

    total_imported = 0

    for filename, source in files.items():
        url = f"https://raw.githubusercontent.com/Molmin/luoguProblems-datas/master/{filename}"
        print(f"  Downloading {filename}...")
        try:
            data = download_json(url)
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

        print(f"  Found {len(data)} problems")

        imported = 0
        for pid, info in data.items():
            title = info.get("title", "")
            difficulty = info.get("difficulty", 0)
            tag_ids = info.get("tags", [])
            tag_names = [TAG_MAP.get(t, f"tag_{t}") for t in tag_ids]
            tags_str = ", ".join(tag_names)
            url_str = f"https://www.luogu.com.cn/problem/{pid}"
            content = f"Luogu {pid}: {title}. Difficulty: {difficulty}. Tags: {tags_str}"

            try:
                conn.execute(
                    "INSERT OR IGNORE INTO problems (source, source_id, title, content, difficulty, tags, url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (source, pid, title, content, str(difficulty), tags_str, url_str)
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    imported += 1
            except sqlite3.Error:
                pass

        conn.commit()
        total_imported += imported
        print(f"  ✓ {filename}: {imported} new problems")

    conn.close()
    return total_imported


def import_luogu_descriptions(db_path: Path, max_problems: int = 0):
    """Import problem descriptions from OldAntique110/Luogu-Problems."""
    conn = sqlite3.connect(str(db_path))

    print("\n📦 Downloading Luogu problem descriptions...")
    print("  Fetching problem list from OldAntique110/Luogu-Problems...")

    # Get list of problem files from GitHub API
    # Since API is rate-limited, we'll try common problem IDs
    # P1000-P1050 are well-known problems

    # Try to get the problem directory listing
    base_url = "https://raw.githubusercontent.com/OldAntique110/Luogu-Problems/master/problem"

    enriched = 0
    failed = 0
    start_pid = 1000
    end_pid = 1050  # Start with a small batch to test

    if max_problems > 0:
        end_pid = start_pid + max_problems

    print(f"  Trying problems P{start_pid}-P{end_pid}...")

    for pid_num in range(start_pid, end_pid + 1):
        pid = f"P{pid_num}"
        url = f"{base_url}/{pid}.md"

        try:
            desc = download_text(url)
            if desc and len(desc) > 50:
                # Clean up markdown
                desc = desc.strip()
                # Update database
                cursor = conn.execute(
                    "UPDATE problems SET content = ? WHERE source = 'luogu' AND source_id = ? AND LENGTH(content) < 300",
                    (desc[:5000], pid)
                )
                if cursor.rowcount > 0:
                    enriched += 1
                else:
                    # Try insert if not exists
                    conn.execute(
                        "INSERT OR IGNORE INTO problems (source, source_id, title, content, difficulty, tags, url) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("luogu", pid, "", desc[:5000], "", "", f"https://www.luogu.com.cn/problem/{pid}")
                    )
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        enriched += 1
            else:
                failed += 1
        except Exception:
            failed += 1

        if (enriched + failed) % 20 == 0 and (enriched + failed) > 0:
            print(f"    ... {enriched + failed} processed | enriched: {enriched} | failed: {failed}")

    conn.commit()
    conn.close()

    print(f"  ✓ Descriptions: {enriched} enriched, {failed} failed")
    return enriched


def main():
    db_path = Path("problem_data/problems.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Import metadata
    metadata_count = import_luogu_metadata(db_path)
    print(f"\n📊 Metadata imported: {metadata_count}")

    # Step 2: Import descriptions (optional, small batch to test)
    if len(sys.argv) > 1 and sys.argv[1] == "--with-desc":
        desc_count = import_luogu_descriptions(db_path, max_problems=100)
        print(f"📊 Descriptions imported: {desc_count}")

    # Summary
    conn = sqlite3.connect(str(db_path))
    total = conn.execute("SELECT COUNT(*) FROM problems WHERE source='luogu'").fetchone()[0]
    print(f"\n✅ Total Luogu problems in database: {total}")
    conn.close()


if __name__ == "__main__":
    main()
