"""
CP-Agent: True Agent architecture with LLM function calling.

The LLM autonomously drives the problem generation workflow by calling tools:
  read_file, write_file, edit_file, list_files,
  compile_cpp, generate_test_data, validate_inputs, run_solution,
  stress_test, search_problem_db, web_search
"""
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from config import (
    PROBLEMS_DIR, DIFFICULTY_PRESETS, ALGO_TOPICS,
    DEFAULT_STRESS_ITERATIONS,
)
from pipeline import execute_tool


def _validate_problem_md_chinese(problem_dir: Path) -> dict:
    """Check whether problem.md is primarily written in Chinese."""
    if problem_dir is None:
        return {"success": False, "message": "未指定 problem 目录"}

    problem_path = problem_dir / "problem.md"
    if not problem_path.exists():
        return {"success": False, "message": "problem.md 不存在"}

    try:
        content = problem_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"success": False, "message": f"读取 problem.md 失败: {e}"}

    in_code_block = False
    text_parts = []
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            text_parts.append(line)
    text = "\n".join(text_parts)

    cjk_count = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    latin_count = sum(1 for ch in text if ("a" <= ch.lower() <= "z"))
    total = cjk_count + latin_count
    cjk_ratio = (cjk_count / total) if total else 0.0

    ok = cjk_count >= 80 and cjk_ratio >= 0.35
    if ok:
        return {
            "success": True,
            "message": f"problem.md 中文校验通过：中文字符 {cjk_count}，中文比例 {cjk_ratio:.2%}",
            "cjk_count": cjk_count,
            "latin_count": latin_count,
            "cjk_ratio": round(cjk_ratio, 4),
        }

    return {
        "success": False,
        "message": (
            "problem.md 中文校验失败：题面必须主要使用中文撰写，"
            f"当前中文字符 {cjk_count}，拉丁字符 {latin_count}，中文比例 {cjk_ratio:.2%}"
        ),
        "cjk_count": cjk_count,
        "latin_count": latin_count,
        "cjk_ratio": round(cjk_ratio, 4),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL DEFINITIONS — JSON Schema for function calling
# ═══════════════════════════════════════════════════════════════════════════════

TOOLS = [
    {
        "name": "read_file",
        "description": "读取文件内容。路径必须是相对路径（沙盒限制在 problem 目录内）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径，如 solution.cpp 或 inputs/01.in"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "创建或覆写文件。路径必须是相对路径。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径，如 solution.cpp"},
                "content": {"type": "string", "description": "文件完整内容"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "搜索替换修改文件。old_text 必须与文件内容完全匹配（包括缩进和换行）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对路径"},
                "old_text": {"type": "string", "description": "要替换的原始文本（必须完全匹配）"},
                "new_text": {"type": "string", "description": "替换后的新文本"}
            },
            "required": ["path", "old_text", "new_text"]
        }
    },
    {
        "name": "list_files",
        "description": "列出目录内容（文件和子目录）。",
        "input_schema": {
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "相对路径，默认 '.'"}
            },
        }
    },
    {
        "name": "compile_cpp",
        "description": "编译 C++ 文件。需要指定源文件和输出路径。输出路径通常为 bin/xxx。",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "源文件相对路径，如 solution.cpp"},
                "output": {"type": "string", "description": "输出二进制相对路径，如 bin/solution"}
            },
            "required": ["source", "output"]
        }
    },
    {
        "name": "generate_test_data",
        "description": "运行已编译的 generator 生成测试数据。generator 必须先编译为 bin/generator。",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "生成的测试数据数量，默认 30"}
            },
        }
    },
    {
        "name": "validate_inputs",
        "description": "运行已编译的 validator 校验所有 inputs/*.in 文件。validator 必须先编译为 bin/validator。",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "run_solution",
        "description": "运行已编译的 solution，为每个 inputs/*.in 生成对应的 outputs/*.out。solution 必须先编译为 bin/solution。",
        "input_schema": {
            "type": "object",
            "properties": {},
        }
    },
    {
        "name": "stress_test",
        "description": "对拍验证：运行 generator 生成随机输入，分别运行 solution 和 naive，比较输出是否一致。solution 和 naive 必须先编译。",
        "input_schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "对拍轮数，默认 1000"}
            },
        }
    },
    {
        "name": "search_problem_db",
        "description": "搜索本地竞赛题库（Codeforces + 洛谷）的相似题，用于原题查重。基于 hybrid 检索：FAISS 向量 + 关键词 + 结构化术语 rerank。构思题目后必须优先调用此工具。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查重关键词或题目核心描述，如 '线段树 区间GCD'"},
                "top_k": {"type": "integer", "description": "返回数量，默认 8，建议 5-10"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_search",
        "description": "搜索网页，返回标题、URL 和摘要。可用于查算法资料、参考已有题目、查 testlib 用法等。",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"]
        }
    },
]


# Convert to OpenAI tools format (used by OpenAI-compatible providers)
def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool defs to OpenAI tools format."""
    result = []
    for t in tools:
        result.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            }
        })
    return result


OPENAI_TOOLS = _to_openai_tools(TOOLS)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
你是 CP-Agent，一个算法竞赛出题专家。你可以通过调用工具来完成整个出题流程。

## 可用工具
- read_file(path) — 读取文件
- write_file(path, content) — 创建/覆写文件
- edit_file(path, old_text, new_text) — 搜索替换修改文件
- list_files(dir) — 列出目录
- compile_cpp(source, output) — 编译 C++
- generate_test_data(count) — 生成测试数据
- validate_inputs() — 校验输入
- run_solution() — 运行标程生成输出
- stress_test(count) — 对拍验证
- search_problem_db(query, top_k) — 搜索本地题库相似题，用于原题查重
- web_search(query) — 搜索网页

## 工作流程
1. 构思题目，生成 problem.md（题面）
2. 必须用 search_problem_db 搜索题目关键词和核心模型，检查是否与已有题目重复。至少搜索 1 次，建议 query 包含算法、数据结构、核心操作和题目对象
3. 如果本地题库搜索结果中出现高度相似的题（题目模型、输入输出、目标函数或核心操作几乎一样），必须换一个题目重新构思。web_search 只作为补充资料搜索，不作为主查重工具
4. 生成 solution.cpp, generator.cpp, validator.cpp, naive.cpp
5. 编译所有 C++ 文件（输出到 bin/ 目录）
6. 运行 generator 生成测试数据（至少 20 组，含边界数据）
7. 运行 validator 校验输入数据
8. 运行 solution 生成输出
9. 运行 stress_test 对拍验证（至少 1000 轮）
10. 如果任何步骤出错，检查错误、修复代码、重试

## 查重判定
- search_problem_db 返回的 final_score 越高越相似；重点看 title、source、source_id、matched_terms 和 snippet
- final_score >= 0.95 且题目模型/操作相近：视为高风险撞题，必须换题
- final_score 0.75-0.95：人工判断相似点，若只是同算法模板但叙事/目标/约束不同可以继续，否则换题
- final_score < 0.75：通常可继续，但仍需避开明显同题

## 重要规则
- problem.md 必须使用中文撰写。标题、题目描述、输入格式、输出格式、样例、样例解释、约束和题解说明都必须是中文；可以保留必要的英文变量名、数学符号和代码块
- 如果你发现 problem.md 是英文或主要不是中文，必须在继续编译/造数据前调用 write_file 或 edit_file 将其完整翻译/改写为中文
- 最终总结前必须确保 problem.md 是中文题面；否则不要结束任务
- generator.cpp 必须基于 testlib.h，使用 #include "testlib.h"
- validator.cpp 必须基于 testlib.h
- testlib.h 位于项目根目录，编译时 -I 会自动包含
- generator 必须接收 argv[1]（测试编号）和 argv[2]（总数）作为参数
- solution.cpp 必须是高效正确的解法，复杂度必须匹配数据规模
- naive.cpp 必须是暴力/朴素解法（用于对拍）
- 所有文件操作必须使用相对路径
- C++ 编译使用 g++ -std=c++17 -O2 -Wall -Wextra
- macOS 没有 bits/stdc++.h，请使用标准头文件（iostream, vector, algorithm 等）

## generator.cpp 模板
```cpp
#include "testlib.h"
#include <iostream>
using namespace std;
int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    int idx = atoi(argv[1]);
    int total = atoi(argv[2]);
    int n = rnd.next(1, 100);  // 根据难度调整
    cout << n << endl;
    for (int i = 0; i < n; i++) {
        cout << rnd.next(1, 1000);
        if (i + 1 < n) cout << " ";
    }
    cout << endl;
    return 0;
}
```

## validator.cpp 模板（重要：必须这样写）
validator 被调用时传入文件路径作为 argv[1]，必须用 registerGen + inf.init 读取文件：
```cpp
#include "testlib.h"
#include <iostream>
using namespace std;
int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    inf.init(argv[1], _input);
    int n = inf.readInt(1, 100000, "n");
    inf.readEoln();
    for (int i = 0; i < n; i++) {
        inf.readInt(1, 1000000, "a[i]");
        if (i + 1 < n) inf.readSpace();
    }
    inf.readEoln();
    inf.readEof();
    return 0;
}
```
注意：不要用 registerValidation()，不要用 registerTestlibCmd()，必须用 registerGen + inf.init。

## 超时处理
如果 run_solution 返回 timeout: true，说明标程复杂度过高，必须：
1. 检查 solution.cpp 的算法复杂度
2. 优化算法（如 O(n²) → O(n log n)）
3. 重新编译并运行
超时意味着标程是错误的，不能忽略

## 最终输出
当所有步骤完成后，用中文总结：
- 题目名称和算法考点
- 数据规模和限制
- 生成了多少组测试数据
- 对拍结果
"""


# ═══════════════════════════════════════════════════════════════════════════════
# WEB SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

def _web_search(query: str) -> dict:
    """Search the web using DuckDuckGo HTML (no API key needed)."""
    try:
        import urllib.request
        import urllib.parse

        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Simple extraction of results
        results = []
        import re
        # Extract result blocks
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL):
            href = m.group(1)
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if title and href:
                results.append({"title": title, "url": href})

        # Extract snippets
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)', html, re.DOTALL)
        for i, s in enumerate(snippets[:len(results)]):
            results[i]["snippet"] = re.sub(r'<[^>]+>', '', s).strip()[:200]

        if not results:
            return {"success": True, "message": "未找到相关结果", "results": []}

        return {"success": True, "results": results[:5]}
    except Exception as e:
        return {"success": False, "message": f"搜索失败: {e}"}


def _search_problem_db(query: str, top_k: int = 8) -> dict:
    """Search local problem DB with hybrid retrieval for duplicate checking."""
    try:
        from problem_db import DB_PATH, INDEX_PATH
        from problem_db.hybrid_search import hybrid_search

        top_k = max(1, min(int(top_k or 8), 20))
        raw_results = hybrid_search(DB_PATH, INDEX_PATH, query, top_k=top_k)

        results = []
        for r in raw_results:
            content = (r.get("content") or r.get("llm_standardized") or "")
            content = " ".join(str(content).split())
            results.append({
                "rank": r.get("rank"),
                "final_score": round(float(r.get("final_score", 0.0)), 4),
                "vector_score": round(float(r.get("vector_score", 0.0)), 4),
                "source": r.get("source", ""),
                "source_id": r.get("source_id", ""),
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "tags": r.get("tags", ""),
                "difficulty": r.get("difficulty", ""),
                "matched_terms": r.get("matched_terms", []),
                "term_coverage": r.get("term_coverage", 0),
                "term_strength": r.get("term_strength", 0),
                "snippet": content[:350],
            })

        return {
            "success": True,
            "message": f"本地题库查重完成：返回 {len(results)} 条",
            "query": query,
            "results": results,
        }
    except Exception as e:
        return {"success": False, "message": f"本地题库搜索失败: {e}", "query": query}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM API — with function calling support
# ═══════════════════════════════════════════════════════════════════════════════

def _call_anthropic_with_tools(messages: list[dict], system: str, model: str,
                                api_key: str, max_tokens: int) -> dict:
    """
    Call Anthropic API with tools.
    Returns {"stop_reason": "tool_use"|"end_turn", "content": [...], "usage": {...}}
    """
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=TOOLS,
    )
    return {
        "stop_reason": resp.stop_reason,
        "content": [{"type": b.type, **({"id": b.id, "name": b.name, "input": b.input} if b.type == "tool_use" else {"text": b.text})} for b in resp.content],
        "usage": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
    }


def _call_openai_with_tools(messages: list[dict], system: str, model: str,
                             base_url: str, api_key: str, max_tokens: int) -> dict:
    """
    Call OpenAI-compatible API with tools.
    Returns {"stop_reason": "tool_calls"|"stop", "content": [...], "usage": {...}}
    """
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)

    # Build messages with system
    api_messages = [{"role": "system", "content": system}] + messages

    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=api_messages,
        tools=OPENAI_TOOLS,
    )

    choice = resp.choices[0]
    msg = choice.message

    # Convert to unified format
    content = []
    if msg.content:
        content.append({"type": "text", "text": msg.content})
    if msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.function.name,
                "input": args,
            })

    stop_reason = "tool_calls" if msg.tool_calls else "stop"
    usage = {}
    if resp.usage:
        usage = {"input": resp.usage.prompt_tokens, "output": resp.usage.completion_tokens}

    return {
        "stop_reason": stop_reason,
        "content": content,
        "usage": usage,
    }


def call_llm_with_tools(messages: list[dict], system: str, provider: str,
                        model: Optional[str] = None, base_url: Optional[str] = None,
                        api_key: Optional[str] = None, max_tokens: int = 16000) -> dict:
    """
    Call LLM API with tool support. Routes to Anthropic or OpenAI based on protocol.
    Returns unified format: {stop_reason, content, usage}
    """
    from config import get_provider

    protocol, cfg = get_provider(provider)
    resolved_model = model or cfg["default_model"]
    resolved_base_url = base_url or cfg["base_url"]
    # API key resolution:
    #   1. CLI --api-key argument
    #   2. config yaml api_key field (direct value)
    #   3. config yaml env_key field: try as env var name first, if not found use as direct key
    cfg_api_key = cfg.get("api_key", "")
    cfg_env_key = cfg.get("env_key", "")
    resolved_api_key = api_key or cfg_api_key
    if not resolved_api_key and cfg_env_key:
        resolved_api_key = os.environ.get(cfg_env_key, "") or cfg_env_key

    if protocol == "anthropic":
        return _call_anthropic_with_tools(messages, system, resolved_model,
                                          resolved_api_key, max_tokens)
    else:
        return _call_openai_with_tools(messages, system, resolved_model,
                                       resolved_base_url, resolved_api_key, max_tokens)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def agent_loop(
    user_prompt: str,
    system_prompt: str = SYSTEM_PROMPT,
    problem_dir: Path = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 16000,
    max_iterations: int = 30,
) -> dict:
    """
    Core agent loop with function calling.

    1. Send user prompt to LLM
    2. If LLM returns tool_use → execute tool → feed result back → repeat
    3. If LLM returns text → done
    4. Cap at max_iterations to prevent infinite loops

    Returns: {"success": bool, "iterations": int, "messages": list, "summary": str}
    """
    from config import get_provider
    protocol, _ = get_provider(provider)

    messages = [{"role": "user", "content": user_prompt}]
    total_input_tokens = 0
    total_output_tokens = 0

    print(f"\n🤖 Agent loop started (max {max_iterations} iterations)")

    for iteration in range(1, max_iterations + 1):
        print(f"\n  ── Iteration {iteration} ──")

        # Call LLM
        try:
            resp = call_llm_with_tools(
                messages, system_prompt, provider,
                model=model, base_url=base_url, api_key=api_key,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"  ✗ LLM call failed: {e}")
            return {
                "success": False,
                "iterations": iteration,
                "messages": messages,
                "summary": f"LLM 调用失败: {e}",
            }

        total_input_tokens += resp.get("usage", {}).get("input", 0)
        total_output_tokens += resp.get("usage", {}).get("output", 0)

        content = resp["content"]
        stop_reason = resp["stop_reason"]

        # Extract text content (for display)
        text_parts = [c["text"] for c in content if c["type"] == "text"]
        tool_parts = [c for c in content if c["type"] == "tool_use"]

        if text_parts:
            for t in text_parts:
                print(f"  💬 {t[:200]}{'...' if len(t) > 200 else ''}")

        if not tool_parts:
            # No tool calls → validate final problem statement before finishing.
            language_check = _validate_problem_md_chinese(problem_dir)
            if not language_check.get("success"):
                print(f"  ✗ {language_check.get('message')}")
                retry_prompt = (
                    "最终校验失败：problem.md 必须是中文题面。\n"
                    f"{language_check.get('message')}\n\n"
                    "请调用 read_file 读取 problem.md，然后调用 write_file 或 edit_file 将 problem.md "
                    "完整改写为中文题面。要求：标题、题目描述、输入格式、输出格式、样例、样例解释、"
                    "约束和算法说明全部使用中文；保留数学公式、变量名和代码块；不要修改已经通过验证的 "
                    "solution.cpp、generator.cpp、validator.cpp、naive.cpp，除非你发现题面与程序不一致。"
                    "修改后再次给出中文总结。"
                )
                if protocol == "anthropic":
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": retry_prompt})
                else:
                    messages.append({
                        "role": "assistant",
                        "content": "".join(text_parts) or None,
                    })
                    messages.append({"role": "user", "content": retry_prompt})
                continue

            print(f"  ✓ {language_check.get('message')}")
            # No tool calls and final validation passed → agent is done
            print(f"\n  ✅ Agent finished after {iteration} iterations")
            print(f"  Tokens: {total_input_tokens} in / {total_output_tokens} out")
            return {
                "success": True,
                "iterations": iteration,
                "messages": messages,
                "summary": "".join(text_parts),
                "tokens": {"input": total_input_tokens, "output": total_output_tokens},
            }

        # Process tool calls
        tool_results = []
        for tc in tool_parts:
            tool_name = tc["name"]
            tool_args = tc["input"]
            tool_id = tc["id"]

            print(f"  🔧 {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:100]})")

            # Special handling for non-sandboxed search tools
            if tool_name == "web_search":
                result = _web_search(tool_args.get("query", ""))
            elif tool_name == "search_problem_db":
                result = _search_problem_db(
                    tool_args.get("query", ""),
                    tool_args.get("top_k", 8),
                )
            else:
                if problem_dir is None:
                    result = {"success": False, "message": "未指定 problem 目录"}
                else:
                    result = execute_tool(problem_dir, tool_name, tool_args)

            # Print result summary
            status = "✓" if result.get("success") else "✗"
            msg = result.get("message", str(result))[:150]
            print(f"    {status} {msg}")

            tool_results.append({
                "tool_use_id": tool_id,
                "tool_name": tool_name,
                "result": result,
            })

        # Add messages in protocol-specific format
        if protocol == "anthropic":
            # Anthropic format: assistant with content blocks, then user with tool_results
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tr["tool_use_id"],
                 "content": json.dumps(tr["result"], ensure_ascii=False)}
                for tr in tool_results
            ]})
        else:
            # OpenAI format: assistant with tool_calls, then separate tool messages
            messages.append({
                "role": "assistant",
                "content": "".join(text_parts) or None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"],
                                  "arguments": json.dumps(tc["input"], ensure_ascii=False)}}
                    for tc in tool_parts
                ],
            })
            for tr in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": json.dumps(tr["result"], ensure_ascii=False),
                })

    # Max iterations reached
    print(f"\n  ⚠ Agent reached max iterations ({max_iterations})")
    return {
        "success": False,
        "iterations": max_iterations,
        "messages": messages,
        "summary": f"达到最大迭代次数 {max_iterations}",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def build_user_prompt(topic: str, difficulty: int, extra: str = "") -> str:
    """Build the user prompt for problem generation."""
    topic_desc = ALGO_TOPICS.get(topic, topic)
    diff_desc = DIFFICULTY_PRESETS.get(difficulty, f"CF {difficulty}")

    return f"""\
请生成一道算法竞赛题目，要求如下：

算法考点：{topic_desc}
难度：Codeforces {difficulty} 分（{diff_desc}）
{f'额外要求：{extra}' if extra else ''}

请根据难度自行决定数据规模、时间限制和内存限制。

语言要求：
- problem.md 必须使用中文撰写
- 标题、题目描述、输入格式、输出格式、样例、样例解释、约束和题解说明都必须是中文
- 可以保留必要的变量名、数学公式和代码块
- 如果生成了英文题面，必须先把 problem.md 完整改写/翻译为中文，再继续后续流程

请按照以下流程操作：
1. 生成所有题目文件（problem.md, solution.cpp, generator.cpp, validator.cpp, naive.cpp）
2. 编译所有 C++ 文件
3. 生成测试数据（至少 20 组）
4. 校验输入数据
5. 运行标程生成输出
6. 对拍验证（至少 1000 轮）

如果任何步骤出错，请检查错误并修复后重试。完成后总结题目信息。
"""


def generate_problem(
    topic: str,
    difficulty: int = 1500,
    extra: str = "",
    problem_name: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 16000,
    max_iterations: int = 30,
    test_count: int = 30,
    stress_iterations: int = DEFAULT_STRESS_ITERATIONS,
    **kwargs,
) -> dict:
    """
    Full agent workflow: LLM drives the entire process via tool calling.
    """
    from config import get_now_model, get_provider
    protocol, cfg = get_provider(provider)
    resolved_model = model or cfg["default_model"]
    resolved_provider = provider or get_now_model()

    # Determine problem name: use --name if given, otherwise timestamp
    if not problem_name:
        from datetime import datetime
        problem_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    problem_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in problem_name)[:50]
    problem_dir = PROBLEMS_DIR / problem_name
    problem_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🤖 CP-Agent: Generating problem on '{topic}' (difficulty: {difficulty})")
    print(f"   Provider: {resolved_provider} ({protocol}), Model: {resolved_model}")
    print(f"   Output dir: {problem_dir}")

    # Build user prompt with problem dir context
    user_prompt = build_user_prompt(topic, difficulty, extra)
    user_prompt += f"\n\n所有文件请写入当前目录（相对路径）。文件操作的根目录已设定为：{problem_dir}"

    # Run agent loop
    result = agent_loop(
        user_prompt=user_prompt,
        problem_dir=problem_dir,
        provider=provider,
        model=model,
        base_url=base_url,
        api_key=api_key,
        max_tokens=max_tokens,
        max_iterations=max_iterations,
    )

    result["problem_dir"] = str(problem_dir)
    result["problem_name"] = problem_name

    if result["success"]:
        print(f"\n🎉 Problem package ready: {problem_dir}")
    else:
        print(f"\n⚠️  Agent 未完成。查看上方日志了解详情。")

    return result


# Legacy entry point (for --pipeline mode, no LLM)
def run_pipeline_only(problem_dir: Path, test_count: int = 30,
                      stress_iterations: int = DEFAULT_STRESS_ITERATIONS,
                      skip_stress: bool = False) -> dict:
    """Run only the pipeline on an existing problem directory (no LLM)."""
    from pipeline import Pipeline
    pipe = Pipeline(problem_dir)
    return pipe.run_full(test_count=test_count, stress_iterations=stress_iterations)
