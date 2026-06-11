"""
Fast Luogu enricher - single-threaded, minimal delay, flush output.
Usage: python problem_db/luogu_enrich_fast.py [max_problems]
"""
import json
import re
import sqlite3
import sys
import time

import requests


def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return s


def fetch(session, pid):
    url = f"https://www.luogu.com.cn/problem/{pid}"
    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return None
        m = re.search(
            r'<script\s+id="lentille-context"\s+type="application/json">(.*?)</script>',
            resp.text, re.DOTALL,
        )
        if not m:
            return None
        data = json.loads(m.group(1))
        problem = data.get("data", {}).get("problem", {})
        contenu = problem.get("contenu", {})
        if not contenu:
            return None
        return {
            "name": problem.get("name", ""),
            "difficulty": problem.get("difficulty", 0),
            "tags": problem.get("tags", []),
            "description": contenu.get("description", ""),
            "formatI": contenu.get("formatI", ""),
            "formatO": contenu.get("formatO", ""),
            "hint": contenu.get("hint", ""),
        }
    except Exception as e:
        return None


def format_content(info):
    parts = []
    if info.get("description"):
        parts.append(info["description"])
    if info.get("formatI"):
        parts.append(f"\n## 输入格式\n{info['formatI']}")
    if info.get("formatO"):
        parts.append(f"\n## 输出格式\n{info['formatO']}")
    if info.get("hint"):
        parts.append(f"\n## 提示\n{info['hint']}")
    return "\n".join(parts)


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
    155: "随机化", 287: "IOI", 318: "IOI", 337: "IOI", 348: "IOI",
    201: "链表", 202: "栈", 203: "队列", 204: "动态规划优化",
    205: "单调栈", 206: "单调队列", 207: "斜率优化", 208: "四边形不等式",
    209: "决策单调性", 210: "CDQ优化DP", 211: "WQS二分",
}


def main():
    max_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    conn = sqlite3.connect("problem_data/problems.db")
    rows = conn.execute(
        "SELECT id, source_id FROM problems "
        "WHERE source = 'luogu' "
        "AND content NOT LIKE '%题目描述%' AND content NOT LIKE '%## %' "
        "ORDER BY source_id"
    ).fetchall()

    if max_problems > 0:
        rows = rows[:max_problems]

    total = len(rows)
    print(f"Found {total} problems to enrich", flush=True)

    session = build_session()
    enriched = 0
    failed = 0
    start = time.time()

    for i, (db_id, pid) in enumerate(rows):
        info = fetch(session, pid)
        if info is None:
            failed += 1
        else:
            content = format_content(info)
            if len(content) < 30:
                failed += 1
            else:
                title = info.get("name", "")
                difficulty = str(info.get("difficulty", ""))
                tag_ids = info.get("tags", [])
                tag_names = [TAG_MAP.get(t, f"tag_{t}") for t in tag_ids]
                tags_str = ", ".join(tag_names)
                conn.execute(
                    "UPDATE problems SET content=?, title=?, difficulty=?, tags=? WHERE id=?",
                    (content, title, difficulty, tags_str, db_id),
                )
                enriched += 1

        done = enriched + failed
        if done % 20 == 0:
            elapsed = time.time() - start
            rate = done / elapsed * 60 if elapsed > 0 else 0
            remaining = (total - done) / rate if rate > 0 else 0
            print(
                f"  [{done}/{total}] ok={enriched} fail={failed} "
                f"({rate:.0f}/min, ~{remaining:.0f}s left)",
                flush=True,
            )
            conn.commit()

        # Minimal delay - just enough to not get rate-limited
        time.sleep(0.3)

    conn.commit()

    # Final summary
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.0f}s", flush=True)
    print(f"  Enriched: {enriched}", flush=True)
    print(f"  Failed:   {failed}", flush=True)
    if elapsed > 0:
        print(f"  Rate:     {enriched / elapsed * 60:.0f}/min", flush=True)

    # Show final DB stats
    total_luogu = conn.execute("SELECT COUNT(*) FROM problems WHERE source='luogu'").fetchone()[0]
    with_desc = conn.execute("SELECT COUNT(*) FROM problems WHERE source='luogu' AND content LIKE '%题目描述%'").fetchone()[0]
    print(f"\nLuogu DB: {with_desc}/{total_luogu} with descriptions ({with_desc*100//total_luogu}%)", flush=True)

    conn.close()


if __name__ == "__main__":
    main()
