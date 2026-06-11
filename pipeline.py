"""
Pipeline: sandboxed tool functions for the Agent.

All file operations are sandboxed to the problem directory.
Each tool returns a structured dict for LLM tool_result consumption.
"""
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from config import CXX, CXX_FLAGS, TESTLIB_PATH, DEFAULT_STRESS_ITERATIONS


# ─── Sandbox helper ──────────────────────────────────────────────────────────

def _sandbox_resolve(problem_dir: Path, path: str) -> tuple[Path, str]:
    """
    Resolve a relative path inside the problem directory sandbox.
    Returns (resolved_path, error_string). error_string is "" on success.
    Rejects absolute paths, path traversal (..), and anything outside problem_dir.
    """
    # Reject absolute paths
    if os.path.isabs(path):
        return Path(""), f"拒绝：不允许绝对路径 '{path}'，必须使用相对路径"

    # Reject path traversal
    if ".." in path.split("/") or ".." in path.split("\\"):
        return Path(""), f"拒绝：不允许路径遍历 '..' in '{path}'"

    resolved = (problem_dir / path).resolve()
    if not str(resolved).startswith(str(problem_dir.resolve())):
        return Path(""), f"拒绝：路径 '{path}' 越界（沙盒限制在 {problem_dir} 内）"

    return resolved, ""


# ─── Low-level helpers ───────────────────────────────────────────────────────

def _run_cmd(cmd: list[str], cwd: str = ".", timeout: int = 60,
             stdin_data: Optional[str] = None) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, input=stdin_data
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"


def _compile(src: Path, out: Path) -> tuple[bool, str]:
    """Compile a C++ file. Returns (success, message)."""
    cmd = [CXX, *CXX_FLAGS, f"-I{TESTLIB_PATH.resolve().parent}",
           str(src.resolve()), "-o", str(out.resolve())]
    code, stdout, stderr = _run_cmd(cmd, timeout=60)
    if code != 0:
        return False, stderr
    return True, f"Compiled {src.name} -> {out.name}"


def _list_dir(dir_path: Path) -> list[str]:
    """List files and dirs in a directory, non-recursive."""
    result = []
    if not dir_path.exists():
        return result
    for p in sorted(dir_path.iterdir()):
        name = p.name
        if p.is_dir():
            name += "/"
        result.append(name)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL FUNCTIONS — 每个 tool 返回 dict，适配 LLM tool_result
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 1. read_file ────────────────────────────────────────────────────────────

def tool_read_file(problem_dir: Path, path: str, max_lines: int = 500,
                   max_chars: int = 20000) -> dict:
    """读取文件内容。返回 {success, content, path}"""
    resolved, err = _sandbox_resolve(problem_dir, path)
    if err:
        return {"success": False, "message": err, "path": path}

    if not resolved.exists():
        return {"success": False, "message": f"文件不存在: {path}", "path": path}
    if not resolved.is_file():
        return {"success": False, "message": f"不是文件: {path}", "path": path}

    try:
        content = resolved.read_text(encoding="utf-8")
        lines = content.split("\n")
        original_chars = len(content)
        if len(lines) > max_lines:
            content = "\n".join(lines[:max_lines]) + f"\n... (截断，共 {len(lines)} 行)"
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n... (截断，共 {original_chars} 字符)"
        return {"success": True, "content": content, "path": path, "lines": len(lines)}
    except Exception as e:
        return {"success": False, "message": f"读取失败: {e}", "path": path}


# ─── 2. write_file ───────────────────────────────────────────────────────────

def tool_write_file(problem_dir: Path, path: str, content: str) -> dict:
    """创建或覆写文件。返回 {success, message, path}"""
    resolved, err = _sandbox_resolve(problem_dir, path)
    if err:
        return {"success": False, "message": err, "path": path}

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return {"success": True, "message": f"已写入 {path} ({lines} 行, {len(content)} 字节)", "path": path}
    except Exception as e:
        return {"success": False, "message": f"写入失败: {e}", "path": path}


# ─── 3. edit_file ────────────────────────────────────────────────────────────

def tool_edit_file(problem_dir: Path, path: str,
                   old_text: str, new_text: str) -> dict:
    """搜索替换修改文件。返回 {success, message, path, replacements}"""
    resolved, err = _sandbox_resolve(problem_dir, path)
    if err:
        return {"success": False, "message": err, "path": path}

    if not resolved.exists():
        return {"success": False, "message": f"文件不存在: {path}", "path": path}

    try:
        content = resolved.read_text(encoding="utf-8")

        if old_text not in content:
            return {
                "success": False,
                "message": f"未找到匹配文本。请检查 old_text 是否与文件内容完全一致（包括缩进和换行）",
                "path": path,
            }

        count = content.count(old_text)
        new_content = content.replace(old_text, new_text)
        resolved.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "message": f"已修改 {path}，替换了 {count} 处",
            "path": path,
            "replacements": count,
        }
    except Exception as e:
        return {"success": False, "message": f"修改失败: {e}", "path": path}


# ─── 4. list_files ───────────────────────────────────────────────────────────

def tool_list_files(problem_dir: Path, dir: str = ".") -> dict:
    """列出目录内容。返回 {success, files, path}"""
    resolved, err = _sandbox_resolve(problem_dir, dir)
    if err:
        return {"success": False, "message": err, "path": dir}

    if not resolved.exists():
        return {"success": False, "message": f"目录不存在: {dir}", "path": dir}
    if not resolved.is_dir():
        return {"success": False, "message": f"不是目录: {dir}", "path": dir}

    files = _list_dir(resolved)
    return {"success": True, "files": files, "path": dir, "count": len(files)}


# ─── 5. compile_cpp ──────────────────────────────────────────────────────────

def tool_compile_cpp(problem_dir: Path, source: str, output: str) -> dict:
    """编译 C++ 文件。返回 {success, message, source, output}"""
    src_resolved, err = _sandbox_resolve(problem_dir, source)
    if err:
        return {"success": False, "message": err}

    out_resolved, err = _sandbox_resolve(problem_dir, output)
    if err:
        return {"success": False, "message": err}

    if not src_resolved.exists():
        return {"success": False, "message": f"源文件不存在: {source}", "source": source}

    out_resolved.parent.mkdir(parents=True, exist_ok=True)
    ok, msg = _compile(src_resolved, out_resolved)

    return {
        "success": ok,
        "message": msg,
        "source": source,
        "output": output,
    }


# ─── 6. generate_test_data ───────────────────────────────────────────────────

def tool_generate_test_data(problem_dir: Path, count: int = 30) -> dict:
    """运行 generator 生成测试数据。返回 {success, message, files_created}"""
    gen_bin = problem_dir.resolve() / "bin" / "generator"
    if not gen_bin.exists():
        return {"success": False, "message": f"generator 未编译，请先 compile_cpp generator.cpp -> bin/generator"}

    inputs_dir = problem_dir.resolve() / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    # 清理旧数据
    for f in inputs_dir.glob("*.in"):
        f.unlink()

    created = []
    errors = []
    for i in range(1, count + 1):
        cmd = [str(gen_bin), str(i), str(count)]
        code, stdout, stderr = _run_cmd(cmd, cwd=str(problem_dir.resolve()), timeout=30)
        if code != 0:
            errors.append(f"test {i}: {stderr[:200]}")
            if len(errors) >= 3:
                break
            continue
        fpath = inputs_dir / f"{i:02d}.in"
        fpath.write_text(stdout)
        created.append(f"{i:02d}.in")

    if errors:
        return {
            "success": False,
            "message": f"生成了 {len(created)} 个，失败 {len(errors)} 个",
            "files_created": created,
            "errors": errors,
        }

    return {
        "success": True,
        "message": f"已生成 {len(created)} 个测试数据",
        "files_created": created,
    }


# ─── 7. validate_inputs ─────────────────────────────────────────────────────

def tool_validate_inputs(problem_dir: Path) -> dict:
    """运行 validator 校验所有输入。返回 {success, message, validated_count, errors}"""
    val_bin = problem_dir.resolve() / "bin" / "validator"
    if not val_bin.exists():
        return {"success": False, "message": "validator 未编译，请先 compile_cpp validator.cpp -> bin/validator"}

    inputs_dir = problem_dir.resolve() / "inputs"
    if not inputs_dir.exists():
        return {"success": False, "message": "inputs/ 目录不存在，请先 generate_test_data"}

    inputs = sorted(inputs_dir.glob("*.in"))
    if not inputs:
        return {"success": False, "message": "inputs/ 目录为空，请先 generate_test_data"}

    errors = []
    count = 0
    for f in inputs:
        cmd = [str(val_bin), str(f)]
        code, stdout, stderr = _run_cmd(cmd, cwd=str(problem_dir.resolve()), timeout=10)
        if code != 0:
            errors.append(f"{f.name}: {stderr[:300]}")
            if len(errors) >= 5:
                break
        else:
            count += 1

    if errors:
        return {
            "success": False,
            "message": f"校验了 {count} 个，失败 {len(errors)} 个",
            "validated_count": count,
            "errors": errors,
        }

    return {
        "success": True,
        "message": f"全部 {count} 个输入校验通过",
        "validated_count": count,
    }


# ─── 8. run_solution ─────────────────────────────────────────────────────────

def tool_run_solution(problem_dir: Path, timeout_sec: int = 5) -> dict:
    """运行 solution 为每个输入生成输出。返回 {success, message, files_created, timeout_files}"""
    sol_bin = problem_dir.resolve() / "bin" / "solution"
    if not sol_bin.exists():
        return {"success": False, "message": "solution 未编译，请先 compile_cpp solution.cpp -> bin/solution"}

    inputs_dir = problem_dir.resolve() / "inputs"
    outputs_dir = problem_dir.resolve() / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    inputs = sorted(inputs_dir.glob("*.in"))
    if not inputs:
        return {"success": False, "message": "inputs/ 为空，请先 generate_test_data"}

    created = []
    errors = []
    timeout_files = []
    for f in inputs:
        inp = f.read_text()
        code, stdout, stderr = _run_cmd(
            [str(sol_bin)], cwd=str(problem_dir.resolve()),
            stdin_data=inp, timeout=timeout_sec
        )
        if code == -1:  # TIMEOUT
            timeout_files.append(f.name)
            errors.append(f"{f.name}: 超时（>{timeout_sec}s）— 标程复杂度可能有误")
            if len(timeout_files) >= 3:
                break
            continue
        if code != 0:
            errors.append(f"{f.name}: {stderr[:200]}")
            if len(errors) >= 3:
                break
            continue
        out_file = outputs_dir / f.with_suffix(".out").name
        out_file.write_text(stdout)
        created.append(out_file.name)

    if timeout_files:
        return {
            "success": False,
            "message": f"超时 {len(timeout_files)} 个（{', '.join(timeout_files[:5])}）— 标程复杂度过高，需要优化算法",
            "files_created": created,
            "errors": errors,
            "timeout": True,
            "timeout_files": timeout_files,
        }

    if errors:
        return {
            "success": False,
            "message": f"生成了 {len(created)} 个输出，失败 {len(errors)} 个",
            "files_created": created,
            "errors": errors,
        }

    return {
        "success": True,
        "message": f"已为 {len(created)} 个输入生成输出",
        "files_created": created,
    }


# ─── 9. stress_test ──────────────────────────────────────────────────────────

def tool_stress_test(problem_dir: Path, count: int = 1000) -> dict:
    """对拍 solution vs naive。返回 {success, message, iterations, mismatches}"""
    import time as _time

    sol_bin = problem_dir.resolve() / "bin" / "solution"
    naive_bin = problem_dir.resolve() / "bin" / "naive"
    gen_bin = problem_dir.resolve() / "bin" / "generator"

    missing = []
    if not sol_bin.exists():
        missing.append("solution")
    if not naive_bin.exists():
        missing.append("naive")
    if not gen_bin.exists():
        missing.append("generator")
    if missing:
        return {"success": False, "message": f"缺少编译产物: {', '.join(missing)}，请先 compile_cpp"}

    TIMEOUT_LIMIT = 10  # 单组测试点总超时（秒）
    mismatches = []
    for i in range(1, count + 1):
        # 生成随机输入
        code, inp, _ = _run_cmd(
            [str(gen_bin), str(i), str(count)],
            cwd=str(problem_dir.resolve()), timeout=10
        )
        if code != 0:
            continue

        # 运行 solution（超时说明标程有误）
        sol_code, sol_out, _ = _run_cmd(
            [str(sol_bin)], cwd=str(problem_dir.resolve()),
            stdin_data=inp, timeout=5
        )
        if sol_code == -1:  # TIMEOUT
            return {
                "success": False,
                "message": f"对拍失败：第 {i} 轮标程超时（>5s）— 标程复杂度有误，需要优化算法",
                "iterations": i,
                "mismatches": [],
                "timeout": True,
            }
        # 运行 naive（计时）
        t_naive = _time.time()
        _, naive_out, _ = _run_cmd(
            [str(naive_bin)], cwd=str(problem_dir.resolve()),
            stdin_data=inp, timeout=15
        )
        naive_elapsed = _time.time() - t_naive

        if naive_elapsed > TIMEOUT_LIMIT:
            return {
                "success": True,
                "message": f"对拍通过：{i} 轮一致，第 {i} 轮暴力解耗时 {naive_elapsed:.1f}s 超过 {TIMEOUT_LIMIT}s 上限，提前结束",
                "iterations": i,
                "mismatches": [],
                "early_exit": True,
            }

        if sol_out.strip() != naive_out.strip():
            mismatches.append({
                "iteration": i,
                "input": inp[:500],
                "solution_output": sol_out.strip()[:200],
                "naive_output": naive_out.strip()[:200],
            })
            if len(mismatches) >= 3:
                break

    if mismatches:
        return {
            "success": False,
            "message": f"对拍失败：{len(mismatches)} 个不匹配（共 {count} 轮）",
            "iterations": count,
            "mismatches": mismatches,
        }

    return {
        "success": True,
        "message": f"对拍通过：{count} 轮全部一致",
        "iterations": count,
        "mismatches": [],
    }


# ─── 10. web_search (stub — 由 agent.py 实现) ───────────────────────────────
# web_search 不在此文件实现，因为它不需要沙盒，由 agent.py 直接处理。

# ═══════════════════════════════════════════════════════════════════════════════
# Tool dispatcher — 根据 tool name 调用对应函数
# ═══════════════════════════════════════════════════════════════════════════════

TOOL_DISPATCHER = {
    "read_file":           lambda pd, args: tool_read_file(pd, args["path"]),
    "write_file":          lambda pd, args: tool_write_file(pd, args["path"], args["content"]),
    "edit_file":           lambda pd, args: tool_edit_file(pd, args["path"], args["old_text"], args["new_text"]),
    "list_files":          lambda pd, args: tool_list_files(pd, args.get("dir", ".")),
    "compile_cpp":         lambda pd, args: tool_compile_cpp(pd, args["source"], args["output"]),
    "generate_test_data":  lambda pd, args: tool_generate_test_data(pd, args.get("count", 30)),
    "validate_inputs":     lambda pd, args: tool_validate_inputs(pd),
    "run_solution":        lambda pd, args: tool_run_solution(pd),
    "stress_test":         lambda pd, args: tool_stress_test(pd, args.get("count", 1000)),
}


def execute_tool(problem_dir: Path, tool_name: str, args: dict) -> dict:
    """Execute a tool by name. Returns structured dict for LLM tool_result."""
    if tool_name not in TOOL_DISPATCHER:
        return {"success": False, "message": f"未知工具: {tool_name}"}
    try:
        return TOOL_DISPATCHER[tool_name](problem_dir, args)
    except Exception as e:
        return {"success": False, "message": f"工具执行异常: {e}"}


# ═══════════════════════════════════════════════════════════════════════════════
# Pipeline class — 向后兼容，内部调用 tool 函数
# ═══════════════════════════════════════════════════════════════════════════════

class Pipeline:
    """Legacy pipeline for --pipeline mode. Wraps tool functions."""

    def __init__(self, problem_dir: Path):
        self.d = problem_dir.resolve()
        self.errors: list[str] = []

    def run_full(self, test_count: int = 20,
                 stress_iterations: int = DEFAULT_STRESS_ITERATIONS) -> dict:
        self.errors = []
        start = time.time()
        results = {}

        print(f"\n{'='*60}")
        print(f"Pipeline: {self.d.name}")
        print(f"{'='*60}")

        steps = [
            ("compile", self._step_compile),
            ("generate", lambda: self._step_generate(test_count)),
            ("validate", self._step_validate),
            ("solve", self._step_solve),
            ("stress_test", lambda: self._step_stress(stress_iterations)),
        ]

        for name, fn in steps:
            print(f"\n[{steps.index((name,fn))+1}/5] {name}...")
            ok = fn()
            results[name] = ok
            if not ok:
                break

        elapsed = time.time() - start
        summary = {
            "problem": self.d.name,
            "results": results,
            "errors": self.errors,
            "elapsed_sec": round(elapsed, 2),
            "all_passed": all(results.values()),
        }
        status = "✅ ALL PASSED" if summary["all_passed"] else "❌ FAILED"
        print(f"\n{'='*60}")
        print(f"Pipeline finished: {status} ({elapsed:.1f}s)")
        if self.errors:
            print(f"Errors ({len(self.errors)}):")
            for e in self.errors[:10]:
                print(f"  - {e}")
        print(f"{'='*60}\n")
        return summary

    def _step_compile(self) -> bool:
        ok = True
        for src_name, out_name in [
            ("generator.cpp", "bin/generator"),
            ("validator.cpp", "bin/validator"),
            ("solution.cpp", "bin/solution"),
            ("naive.cpp", "bin/naive"),
        ]:
            src = self.d / src_name
            if not src.exists():
                continue
            r = tool_compile_cpp(self.d, src_name, out_name)
            if not r["success"]:
                self.errors.append(f"[COMPILE] {src_name}: {r['message']}")
                ok = False
            else:
                print(f"  ✓ {r['message']}")
        return ok

    def _step_generate(self, count: int) -> bool:
        r = tool_generate_test_data(self.d, count)
        if not r["success"]:
            self.errors.append(f"[GENERATE] {r['message']}")
            return False
        print(f"  ✓ {r['message']}")
        return True

    def _step_validate(self) -> bool:
        r = tool_validate_inputs(self.d)
        if not r["success"]:
            self.errors.append(f"[VALIDATE] {r['message']}")
            if r.get("errors"):
                self.errors.extend(r["errors"][:3])
            return False
        print(f"  ✓ {r['message']}")
        return True

    def _step_solve(self) -> bool:
        r = tool_run_solution(self.d)
        if not r["success"]:
            self.errors.append(f"[SOLVE] {r['message']}")
            return False
        print(f"  ✓ {r['message']}")
        return True

    def _step_stress(self, iterations: int) -> bool:
        r = tool_stress_test(self.d, iterations)
        if not r["success"]:
            self.errors.append(f"[STRESS] {r['message']}")
            if r.get("mismatches"):
                for m in r["mismatches"][:3]:
                    self.errors.append(f"  mismatch at iter {m['iteration']}")
            return False
        print(f"  ✓ {r['message']}")
        return True
