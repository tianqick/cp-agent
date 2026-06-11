#!/usr/bin/env python3
"""
CP-Agent CLI: Automated Competitive Programming Problem Generator

Usage:
    # Agent 模式（默认）— LLM 自主调用 tool 完成全流程
    python main.py --topic dp --difficulty medium
    python main.py --topic graph --difficulty hard --provider deepseek
    python main.py --topic tree --difficulty easy --provider mimo --max-iterations 50

    # Pipeline 模式 — 直接运行已有题目的流水线（无 LLM）
    python main.py --pipeline problems/my_problem/

    # 信息查询
    python main.py --list-topics
    python main.py --list-providers
"""
import argparse
import sys
from pathlib import Path

from config import (
    ALGO_TOPICS,
    DIFFICULTY_PRESETS,
    LLM_PROVIDERS,
    get_now_model,
    list_enabled_provider_choices,
)


def list_topics():
    print("\nAvailable algorithm topics:")
    print("-" * 50)
    for key, desc in ALGO_TOPICS.items():
        print(f"  {key:<20} {desc}")
    print()


def list_difficulties():
    print("\nAvailable difficulty levels (Codeforces rating):")
    print("-" * 60)
    for score, desc in DIFFICULTY_PRESETS.items():
        print(f"  {score:<6} {desc}")
    print()


def list_providers():
    print("\nAvailable LLM providers:")
    print("-" * 80)
    print(f"  Current nowModel: {get_now_model() or 'N/A'}")
    print()
    print(f"  {'Protocol':<12} {'Provider':<14} {'Default Model':<30} {'Env Var':<22} {'Enabled'}")
    print(f"  {'-'*10:<12} {'-'*12:<14} {'-'*28:<30} {'-'*20:<22} {'-'*7}")
    for protocol, providers in LLM_PROVIDERS.items():
        for name, cfg in providers.items():
            enabled = "✓" if cfg.get("enabled", True) else "✗"
            env = cfg.get("env_key", "") or "N/A"
            print(f"  {protocol:<12} {name:<14} {cfg['default_model']:<30} {env:<22} {enabled}")
    print()
    print("  Tips:")
    print("  - Set enabled: false in config.yaml to disable a provider")
    print("  - For custom endpoints: --provider openai --base-url <url> --api-key <key>")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="CP-Agent: Automated CP Problem Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Problem options ──
    parser.add_argument("--topic", "-t", type=str,
                        help="Algorithm topic (e.g., dp, graph, tree, greedy)")
    parser.add_argument("--difficulty", "-d", type=int, default=1500,
                        help="Codeforces rating 800-3000 (default: 1500)")
    parser.add_argument("--name", "-n", type=str, default=None,
                        help="Problem name (directory name)")
    parser.add_argument("--extra", "-e", type=str, default="",
                        help="Extra requirements for problem generation")

    # ── LLM provider options ──
    enabled_names = list_enabled_provider_choices()
    parser.add_argument("--provider", "-P", type=str, default=None,
                        choices=enabled_names,
                        help="LLM provider override (default: config.yaml nowModel)")
    parser.add_argument("--model", "-m", type=str, default=None,
                        help="Model name (default: provider's default)")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Custom API base URL (overrides provider default)")
    parser.add_argument("--api-key", type=str, default=None,
                        help="API key (overrides env var)")
    parser.add_argument("--max-iterations", type=int, default=30,
                        help="Max agent loop iterations (default: 30)")
    parser.add_argument("--max-tokens", type=int, default=16000,
                        help="Max tokens per LLM call (default: 16000)")

    # ── Pipeline options ──
    parser.add_argument("--test-count", type=int, default=30,
                        help="Number of test cases to generate (default: 30)")
    parser.add_argument("--stress", "-s", type=int, default=10000,
                        help="Stress test iterations (default: 10000)")
    parser.add_argument("--pipeline", "-p", type=str, default=None,
                        help="Run pipeline only on existing problem directory (no LLM)")

    # ── Info commands ──
    parser.add_argument("--list-topics", action="store_true",
                        help="List available algorithm topics")
    parser.add_argument("--list-difficulties", action="store_true",
                        help="List available difficulty levels")
    parser.add_argument("--list-providers", action="store_true",
                        help="List available LLM providers")

    args = parser.parse_args()

    if args.list_topics:
        list_topics()
        return

    if args.list_difficulties:
        list_difficulties()
        return

    if args.list_providers:
        list_providers()
        return

    # ── Pipeline mode (no LLM) ──
    if args.pipeline:
        from agent import run_pipeline_only
        problem_dir = Path(args.pipeline)
        if not problem_dir.exists():
            print(f"Error: {problem_dir} does not exist")
            sys.exit(1)
        run_pipeline_only(problem_dir, args.test_count, args.stress)
        return

    # ── Agent mode (default) ──
    if not args.topic:
        parser.error("--topic is required (or use --pipeline or --list-topics)")

    from agent import generate_problem
    result = generate_problem(
        topic=args.topic,
        difficulty=args.difficulty,
        extra=args.extra,
        problem_name=args.name,
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
        max_tokens=args.max_tokens,
        max_iterations=args.max_iterations,
        test_count=args.test_count,
        stress_iterations=args.stress,
    )

    if result.get("success"):
        print(f"\n🎉 Problem package ready: {result.get('problem_dir', 'unknown')}")
    else:
        print(f"\n⚠️  Agent 未完成: {result.get('summary', 'unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
