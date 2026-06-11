"""
Fast rule-based problem preprocessor for standardizing problem descriptions.
No LLM required - uses pattern matching and heuristics.
"""
import re
import sqlite3
from pathlib import Path

# Algorithm type mapping from tags
ALGORITHM_MAP = {
    'dp': '动态规划',
    'dynamic programming': '动态规划',
    '贪心': '贪心',
    'greedy': '贪心',
    '图论': '图论',
    'graph': '图论',
    '树形dp': '树形DP',
    'trees': '树',
    'tree': '树',
    '最小生成树': '最小生成树',
    '二分': '二分',
    'binary search': '二分',
    '数据结构': '数据结构',
    'data structures': '数据结构',
    '数学': '数学',
    'math': '数学',
    '数论': '数论',
    'number theory': '数论',
    '字符串': '字符串',
    'string': '字符串',
    '搜索': '搜索',
    'dfs': '搜索',
    'bfs': '搜索',
    'search': '搜索',
    '模拟': '模拟',
    'implementation': '模拟',
    'constructive': '构造',
    '构造': '构造',
    'bitmasks': '位运算',
    '位运算': '位运算',
    'brute force': '暴力',
    '暴力': '暴力',
    'sorting': '排序',
    '排序': '排序',
    'geometry': '几何',
    '几何': '几何',
    'combinatorics': '组合数学',
    '组合数学': '组合数学',
    'probabilities': '概率',
    '概率': '概率',
    'games': '博弈论',
    '博弈': '博弈论',
}

# Difficulty level mapping
DIFFICULTY_MAP = {
    '入门': '入门',
    'entry': '入门',
    'easy': '入门',
    '普及': '普及',
    '普及-': '普及',
    '普及/提高-': '普及',
    '提高': '提高',
    '提高+': '提高',
    '省选': '省选',
    '省选/NOI-': '省选',
    'NOI': 'NOI',
    'NOI+': 'NOI',
    'CTSC': '国集',
    '800': '入门',
    '900': '入门',
    '1000': '入门',
    '1100': '入门',
    '1200': '普及',
    '1300': '普及',
    '1400': '普及',
    '1500': '提高',
    '1600': '提高',
    '1700': '提高',
    '1800': '省选',
    '1900': '省选',
    '2000': '省选',
    '2100': '省选',
    '2200': 'NOI',
    '2300': 'NOI',
    '2400': 'NOI',
    '2500': 'NOI',
    '2600': '国集',
    '2700': '国集',
    '2800': '国集',
    '2900': '国集',
    '3000': '国集',
}

# Data structure patterns. Specific terms are trusted only when they appear in
# title/content; tags are noisy in this dataset and are kept as hints.
SPECIFIC_DATA_STRUCTURE_PATTERNS = [
    (r'线段树|segment\s*tree|segtree', '线段树'),
    (r'树状数组|fenwick|binary\s*indexed', '树状数组'),
    (r'并查集|dsu|disjoint\s*set|union\s*find', '并查集'),
    (r'主席树|可持久化线段树|persistent\s*segment\s*tree', '主席树'),
    (r'树链剖分|heavy\s*light|hld', '树链剖分'),
    (r'字典树|trie', '字典树'),
    (r'后缀数组|suffix\s*array', '后缀数组'),
    (r'后缀自动机|suffix\s*automaton', '后缀自动机'),
    (r'平衡树|balanced\s*tree|splay|treap|avl', '平衡树'),
    (r'单调队列|monotonic\s*queue', '单调队列'),
    (r'单调栈|monotonic\s*stack', '单调栈'),
]

GENERIC_DATA_STRUCTURE_PATTERNS = [
    (r'栈|stack', '栈'),
    (r'队列|queue', '队列'),
    (r'堆|heap|priority\s*queue', '堆'),
    (r'哈希|hash', '哈希表'),
    (r'链表|linked\s*list', '链表'),
    (r'树|tree', '树'),
    (r'图|graph', '图'),
    (r'数组|array', '数组'),
    (r'矩阵|matrix', '矩阵'),
]

# Core operation patterns
CORE_OPERATION_PATTERNS = [
    (r'求和|sum|add', '求和'),
    (r'最大值|maximum|max', '求最大值'),
    (r'最小值|minimum|min', '求最小值'),
    (r'计数|count', '计数'),
    (r'排序|sort', '排序'),
    (r'搜索|search|查找|find', '搜索'),
    (r'遍历|traverse', '遍历'),
    (r'合并|merge', '合并'),
    (r'分割|split', '分割'),
    (r'匹配|match', '匹配'),
    (r'路径|path', '路径搜索'),
    (r'连通|connect', '连通性'),
    (r'最短路|shortest', '最短路径'),
    (r'最长|longest', '最长路径'),
    (r'子序列|subsequence', '子序列'),
    (r'子串|substring', '子串'),
    (r'区间|interval|range', '区间操作'),
    (r'更新|update', '更新'),
    (r'查询|query', '查询'),
]


DATA_STRUCTURE_TAGS = {
    "线段树", "segment tree", "segtree",
    "树状数组", "fenwick", "binary indexed tree",
    "并查集", "dsu", "disjoint set union", "union find",
    "主席树", "可持久化线段树", "树链剖分", "hld",
    "字典树", "trie", "后缀数组", "后缀自动机",
}


def _split_tags(tags: str) -> list[str]:
    if not tags:
        return []
    return [t.strip().lower() for t in re.split(r"[,，;；/]+", tags) if t.strip()]


def extract_algorithm(tags: str) -> str:
    """Extract algorithm type from tags."""
    if not tags:
        return "未知"

    algorithms = []
    tag_tokens = _split_tags(tags)

    for token in tag_tokens:
        if token in DATA_STRUCTURE_TAGS:
            continue
        if token in ALGORITHM_MAP:
            algorithms.append(ALGORITHM_MAP[token])
            continue
        # Keep English CF tags like "dfs and similar" usable without letting
        # Chinese substrings such as "线段树" trigger generic "树".
        if re.search(r"[a-z]", token):
            for key, value in ALGORITHM_MAP.items():
                if re.search(r"[a-z]", key) and key in token:
                    algorithms.append(value)

    if algorithms:
        return "、".join(_dedupe(algorithms)[:3])  # Return top 3
    return "未知"


def extract_difficulty_level(difficulty: str) -> str:
    """Extract difficulty level from difficulty string."""
    if not difficulty:
        return "未知"

    # Try direct match
    for key, value in DIFFICULTY_MAP.items():
        if key in difficulty:
            return value

    # Try numeric match
    numbers = re.findall(r'\d+', difficulty)
    if numbers:
        rating = int(numbers[0])
        if rating <= 1100:
            return "入门"
        elif rating <= 1400:
            return "普及"
        elif rating <= 1700:
            return "提高"
        elif rating <= 2100:
            return "省选"
        elif rating <= 2500:
            return "NOI"
        else:
            return "国集"

    return "未知"


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_data_structure(title: str, content: str, tags: str) -> tuple[str, str]:
    """
    Extract data structures from trusted text and keep tag-only matches as hints.

    Specific structures like 线段树/树状数组 are only written to
    llm_data_structure when title/content confirms them. Luogu tags are noisy
    enough that tag-only matches should not become hard structured fields.
    """
    trusted_text = f"{title} {content}".lower()
    tags_text = (tags or "").lower()
    structures = []
    tag_hints = []

    for pattern, value in SPECIFIC_DATA_STRUCTURE_PATTERNS:
        if re.search(pattern, trusted_text):
            structures.append(value)
        elif re.search(pattern, tags_text):
            tag_hints.append(value)

    if not structures:
        for pattern, value in GENERIC_DATA_STRUCTURE_PATTERNS:
            if re.search(pattern, trusted_text):
                structures.append(value)
            elif re.search(pattern, tags_text):
                tag_hints.append(value)

    if structures:
        return "、".join(_dedupe(structures)[:3]), "、".join(_dedupe(tag_hints)[:5])
    return "无特殊数据结构", "、".join(_dedupe(tag_hints)[:5])


def extract_core_operation(content: str) -> str:
    """Extract core operation from content."""
    if not content:
        return "未知"

    content_lower = content.lower()
    operations = []

    for pattern, value in CORE_OPERATION_PATTERNS:
        if re.search(pattern, content_lower):
            operations.append(value)

    if operations:
        return "、".join(operations[:2])  # Return top 2
    return "未知"


def generate_standardized_description(title: str, content: str, algorithm: str,
                                       data_structure: str, core_operation: str,
                                       difficulty_level: str,
                                       tag_structure_hints: str = "") -> str:
    """Generate a standardized description."""
    # Extract first 200 chars of content as base
    base = content[:200] if content else ""

    # Build standardized description
    parts = []
    if algorithm and algorithm != "未知":
        parts.append(f"算法类型：{algorithm}")
    if data_structure and data_structure != "无特殊数据结构":
        parts.append(f"数据结构：{data_structure}")
    if core_operation and core_operation != "未知":
        parts.append(f"核心操作：{core_operation}")
    if difficulty_level and difficulty_level != "未知":
        parts.append(f"难度：{difficulty_level}")
    if tag_structure_hints:
        parts.append(f"标签提示数据结构：{tag_structure_hints}")

    if parts:
        return f"{'，'.join(parts)}。{base}"
    return base


def preprocess_problem_fast(title: str, content: str, tags: str, difficulty: str) -> dict:
    """
    Fast rule-based preprocessing for a single problem.

    Returns:
        Standardized problem dict with algorithm, data_structure, etc.
    """
    algorithm = extract_algorithm(tags)
    difficulty_level = extract_difficulty_level(difficulty)
    data_structure, tag_structure_hints = extract_data_structure(title, content, tags)
    core_operation = extract_core_operation(content)

    standardized_description = generate_standardized_description(
        title, content, algorithm, data_structure, core_operation,
        difficulty_level, tag_structure_hints
    )

    return {
        "algorithm": algorithm,
        "data_structure": data_structure,
        "core_operation": core_operation,
        "difficulty_level": difficulty_level,
        "standardized_description": standardized_description,
        "tag_structure_hints": tag_structure_hints,
    }


def preprocess_problems_batch_fast(db_path: Path, max_problems: int = 0,
                                   force: bool = False) -> int:
    """
    Batch preprocess all problems using fast rule-based approach.

    Args:
        db_path: Path to SQLite database
        max_problems: Maximum number of problems to process (0 = all)

    Returns:
        Number of successfully processed problems
    """
    conn = sqlite3.connect(str(db_path))

    # Check if llm_standardized column exists
    cursor = conn.execute("PRAGMA table_info(problems)")
    columns = [row[1] for row in cursor.fetchall()]

    if "llm_standardized" not in columns:
        conn.execute("ALTER TABLE problems ADD COLUMN llm_standardized TEXT")
        conn.execute("ALTER TABLE problems ADD COLUMN llm_algorithm TEXT")
        conn.execute("ALTER TABLE problems ADD COLUMN llm_data_structure TEXT")
        conn.execute("ALTER TABLE problems ADD COLUMN llm_core_operation TEXT")
        conn.execute("ALTER TABLE problems ADD COLUMN llm_difficulty_level TEXT")
        conn.commit()
        print("✓ Added preprocessing columns to database")

    # Get problems to process
    where = "content != ''" if force else "llm_standardized IS NULL AND content != ''"
    if max_problems > 0:
        rows = conn.execute(
            "SELECT id, title, content, tags, difficulty FROM problems "
            f"WHERE {where} "
            "ORDER BY id LIMIT ?",
            (max_problems,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title, content, tags, difficulty FROM problems "
            f"WHERE {where}"
        ).fetchall()

    if not rows:
        print("✓ No problems to process")
        conn.close()
        return 0

    mode = "force overwrite" if force else "missing only"
    print(f"📊 {len(rows)} problems to preprocess (fast mode, {mode})")

    success_count = 0
    fail_count = 0

    for i, (pid, title, content, tags, difficulty) in enumerate(rows):
        try:
            # Fast preprocessing
            result = preprocess_problem_fast(
                title=title or "",
                content=content or "",
                tags=tags or "",
                difficulty=difficulty or ""
            )

            # Update database
            conn.execute(
                """UPDATE problems SET
                   llm_standardized = ?,
                   llm_algorithm = ?,
                   llm_data_structure = ?,
                   llm_core_operation = ?,
                   llm_difficulty_level = ?
                   WHERE id = ?""",
                (
                    result.get("standardized_description", ""),
                    result.get("algorithm", ""),
                    result.get("data_structure", ""),
                    result.get("core_operation", ""),
                    result.get("difficulty_level", ""),
                    pid
                )
            )

            success_count += 1

            # Progress output
            if (i + 1) % 1000 == 0 or (i + 1) == len(rows):
                print(f"  [{i+1}/{len(rows)}] ✓ {pid} {title[:30]}...")

            # Commit every 1000 problems
            if (i + 1) % 1000 == 0:
                conn.commit()

        except Exception as e:
            fail_count += 1
            print(f"  [{i+1}/{len(rows)}] ✗ {pid} {title[:30]}... Error: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"\n✅ 快速预处理完成:")
    print(f"  成功: {success_count}, 失败: {fail_count}")

    return success_count


if __name__ == "__main__":
    # Test with a single problem
    test_result = preprocess_problem_fast(
        title="A+B Problem",
        content="输入两个整数a和b，输出它们的和。",
        tags="入门,模拟",
        difficulty="入门"
    )
    import json
    print(json.dumps(test_result, indent=2, ensure_ascii=False))
