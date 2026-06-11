"""
LLM-based problem preprocessor for standardizing problem descriptions
before vectorization. Improves embedding quality by normalizing different
phrasings of similar problems.
"""
import json
import sqlite3
import time
import re
from pathlib import Path
from typing import Optional

# System prompt for problem standardization
SYSTEM_PROMPT = """你是一个OI（信息学奥林匹克）题目分析专家。你的任务是将竞赛编程题目标准化，使其更适合向量化检索。

对于每道题目，请提取以下信息：
1. 算法类型：主要考察的算法（如：动态规划、图论、贪心、数据结构等）
2. 数据结构：涉及的数据结构（如：数组、树、图、栈、队列等）
3. 核心操作：题目的核心操作或思路（如：遍历、搜索、排序、合并等）
4. 难度评估：基于OI标准的难度（入门/普及/提高/省选/NOI/国集）
5. 标准化描述：用简洁、统一的语言描述题目的核心要求，去掉具体的输入输出格式细节

请用JSON格式输出，包含以下字段：
{
  "algorithm": "算法类型",
  "data_structure": "数据结构",
  "core_operation": "核心操作",
  "difficulty_level": "难度等级",
  "standardized_description": "标准化描述（100-200字）"
}"""

USER_PROMPT_TEMPLATE = """请分析以下OI题目并标准化：

标题：{title}
标签：{tags}
难度：{difficulty}

题目描述：
{content}

请按照要求输出JSON格式的分析结果。"""


def _call_llm_simple(messages: list[dict], system: str, provider: str,
                     api_key: Optional[str] = None, max_tokens: int = 1000,
                     model: Optional[str] = None) -> str:
    """
    Simple LLM call without tools. Uses the same provider logic as agent.py.
    Returns the raw response text.
    """
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import get_provider

    # Get provider config
    protocol, provider_cfg = get_provider(provider)

    base_url = provider_cfg.get("base_url", "")
    resolved_model = model or provider_cfg.get("default_model", "")
    resolved_api_key = api_key or provider_cfg.get("api_key", "")
    env_key = provider_cfg.get("env_key", "")
    if not resolved_api_key and env_key:
        resolved_api_key = os.environ.get(env_key, "") or env_key

    if protocol == "anthropic":
        # Use Anthropic SDK
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=resolved_api_key)
            response = client.messages.create(
                model=resolved_model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                temperature=0.3
            )
            return response.content[0].text
        except ImportError:
            print("  ⚠️ anthropic package not installed. Run: pip install anthropic")
            raise
    else:
        # Use OpenAI SDK for all other providers
        try:
            from openai import OpenAI
        except ImportError:
            print("  ⚠️ openai package not installed. Run: pip install openai")
            raise

        client = OpenAI(base_url=base_url, api_key=resolved_api_key)
        api_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model=resolved_model,
            messages=api_messages,
            temperature=0.3,
            max_tokens=max_tokens
        )
        result = response.choices[0].message.content
        if result:
            return result.strip()
        return ""


def preprocess_problem(title: str, content: str, tags: str, difficulty: str,
                       provider: str = "deepseek", api_key: Optional[str] = None,
                       model: Optional[str] = None) -> dict:
    """
    Use LLM to preprocess and standardize a single problem.

    Args:
        title: Problem title
        content: Problem description
        tags: Problem tags
        difficulty: Problem difficulty
        provider: LLM provider to use (deepseek, ollama, openai, etc.)
        api_key: Optional API key override

    Returns:
        Standardized problem dict with algorithm, data_structure, etc.
    """
    # Prepare the user message
    user_message = USER_PROMPT_TEMPLATE.format(
        title=title,
        tags=tags,
        difficulty=difficulty,
        content=content[:2000]  # Limit content length to avoid token limits
    )

    messages = [{"role": "user", "content": user_message}]

    try:
        # Call LLM
        result_text = _call_llm_simple(messages, SYSTEM_PROMPT, provider, api_key, model=model)

        # Try to extract JSON from the response
        # Handle cases where LLM wraps JSON in markdown code blocks
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # Find JSON object in the text
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start != -1 and end != -1:
            result_text = result_text[start:end]

        result = json.loads(result_text)
        return result

    except Exception as e:
        print(f"  ⚠️ LLM预处理失败: {e}")
        # Fallback: return basic structure
        return {
            "algorithm": tags,
            "data_structure": "未知",
            "core_operation": "未知",
            "difficulty_level": difficulty,
            "standardized_description": f"{title}: {content[:200]}"
        }


def preprocess_problems_batch(db_path: Path, max_problems: int = 0,
                               provider: str = "deepseek", delay: float = 1.0,
                               api_key: Optional[str] = None,
                               force: bool = False,
                               problem_ids: Optional[list[int]] = None,
                               model: Optional[str] = None) -> int:
    """
    Batch preprocess all problems in the database using LLM.

    Args:
        db_path: Path to SQLite database
        max_problems: Maximum number of problems to process (0 = all)
        provider: LLM provider to use
        delay: Delay between API calls in seconds
        api_key: Optional API key override

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
        print("✓ Added LLM preprocessing columns to database")

    # Get problems to process
    if problem_ids:
        placeholders = ",".join("?" for _ in problem_ids)
        limit_sql = " LIMIT ?" if max_problems > 0 else ""
        params = [*problem_ids]
        if max_problems > 0:
            params.append(max_problems)
        rows = conn.execute(
            "SELECT id, title, content, tags, difficulty FROM problems "
            f"WHERE id IN ({placeholders}) AND content != '' "
            f"ORDER BY id{limit_sql}",
            params,
        ).fetchall()
    elif max_problems > 0:
        where = "content != ''" if force else "llm_standardized IS NULL AND content != ''"
        rows = conn.execute(
            "SELECT id, title, content, tags, difficulty FROM problems "
            f"WHERE {where} "
            "ORDER BY id LIMIT ?",
            (max_problems,)
        ).fetchall()
    else:
        where = "content != ''" if force else "llm_standardized IS NULL AND content != ''"
        rows = conn.execute(
            "SELECT id, title, content, tags, difficulty FROM problems "
            f"WHERE {where}"
        ).fetchall()

    if not rows:
        print("✓ No problems to process")
        conn.close()
        return 0

    mode = "selected ids" if problem_ids else ("force overwrite" if force else "missing only")
    model_desc = f", Model: {model}" if model else ""
    print(f"📊 {len(rows)} problems to preprocess with LLM ({mode})")
    print(f"  Provider: {provider}{model_desc}, Delay: {delay}s")

    success_count = 0
    fail_count = 0

    for i, (pid, title, content, tags, difficulty) in enumerate(rows):
        try:
            # Call LLM to preprocess
            result = preprocess_problem(
                title=title or "",
                content=content or "",
                tags=tags or "",
                difficulty=difficulty or "",
                provider=provider,
                api_key=api_key,
                model=model,
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
            if (i + 1) % 10 == 0 or (i + 1) == len(rows):
                print(f"  [{i+1}/{len(rows)}] ✓ {pid} {title[:30]}...")

            # Commit every 50 problems
            if (i + 1) % 50 == 0:
                conn.commit()

            # Rate limiting
            time.sleep(delay)

        except Exception as e:
            fail_count += 1
            print(f"  [{i+1}/{len(rows)}] ✗ {pid} {title[:30]}... Error: {e}")
            continue

    conn.commit()
    conn.close()

    print(f"\n✅ LLM预处理完成:")
    print(f"  成功: {success_count}, 失败: {fail_count}")

    return success_count


VECTOR_TEXT_VERSION = "v2_title_content_first"


def _clean_for_embedding(text: str, max_chars: int) -> str:
    """Light cleanup for embedding input; keep semantic text, drop spacing noise."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    return text[:max_chars]


def get_standardized_text(row: tuple) -> str:
    """
    Get standardized text for vectorization from a problem row.

    Args:
        row: Tuple of (id, title, content, tags, difficulty, llm_standardized,
             llm_algorithm, llm_data_structure, llm_core_operation, llm_difficulty_level)

    Returns:
        Standardized text for vectorization
    """
    # Handle both 9-column and 10-column tuples
    if len(row) == 10:
        pid, title, content, tags, difficulty, llm_standardized, llm_algorithm, llm_data_structure, llm_core_operation, llm_difficulty_level = row
    elif len(row) == 9:
        title, content, tags, difficulty, llm_standardized, llm_algorithm, llm_data_structure, llm_core_operation, llm_difficulty_level = row
    else:
        raise ValueError(f"Expected 9 or 10 columns, got {len(row)}")

    title = _clean_for_embedding(title, 200)
    tags = _clean_for_embedding(tags, 300)
    difficulty = _clean_for_embedding(difficulty, 80)
    content = _clean_for_embedding(content, 1400)
    llm_algorithm = _clean_for_embedding(llm_algorithm, 160)
    llm_data_structure = _clean_for_embedding(llm_data_structure, 160)
    llm_core_operation = _clean_for_embedding(llm_core_operation, 160)
    llm_difficulty_level = _clean_for_embedding(llm_difficulty_level, 80)
    llm_standardized = _clean_for_embedding(llm_standardized, 600)

    parts = [
        f"题目标题：{title}",
        f"原始标签：{tags}",
        f"难度：{difficulty}",
        f"题面摘要：{content}",
    ]

    structured = []
    if llm_algorithm:
        structured.append(f"算法类型：{llm_algorithm}")
    if llm_data_structure:
        structured.append(f"数据结构：{llm_data_structure}")
    if llm_core_operation:
        structured.append(f"核心操作：{llm_core_operation}")
    if llm_difficulty_level:
        structured.append(f"预处理难度：{llm_difficulty_level}")
    if llm_standardized:
        structured.append(f"标准化描述：{llm_standardized}")

    if structured:
        # These fields are useful, but noisier than title/content in this DB.
        parts.append("结构化参考：" + "；".join(structured))

    return "\n".join(parts)


if __name__ == "__main__":
    # Test with a single problem
    test_result = preprocess_problem(
        title="A+B Problem",
        content="输入两个整数a和b，输出它们的和。",
        tags="入门,模拟",
        difficulty="入门",
        provider="deepseek"
    )
    print(json.dumps(test_result, indent=2, ensure_ascii=False))
