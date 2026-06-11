"""
CP-Agent configuration loader.
Reads from config.yaml and exposes the same interface as before.
"""
import os
from pathlib import Path

import yaml

# ─── Load YAML ───────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
_yaml_path = PROJECT_ROOT / "config.yaml"

with open(_yaml_path, "r", encoding="utf-8") as _f:
    _cfg = yaml.safe_load(_f)

# ─── Paths ───────────────────────────────────────────────────────────────────
PROBLEMS_DIR = PROJECT_ROOT / "problems"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
BIN_DIR = PROJECT_ROOT / "bin"
TESTLIB_PATH = PROJECT_ROOT / _cfg.get("testlib", "testlib.h")

# ─── Compiler ────────────────────────────────────────────────────────────────
CXX = os.environ.get("CXX", _cfg.get("cxx", "g++"))
CXX_FLAGS = _cfg.get("cxx_flags", ["-std=c++17", "-O2", "-Wall", "-Wextra"])

# ─── Problem limits ──────────────────────────────────────────────────────────
DEFAULT_TIME_LIMIT_MS = _cfg.get("time_limit_ms", 1000)
DEFAULT_MEMORY_LIMIT_MB = _cfg.get("memory_limit_mb", 256)

# ─── Difficulty presets ──────────────────────────────────────────────────────
DIFFICULTY_PRESETS = _cfg.get("difficulty", {})

# ─── Stress test ─────────────────────────────────────────────────────────────
DEFAULT_STRESS_ITERATIONS = _cfg.get("stress_iterations", 10000)
DEFAULT_STRESS_TIMEOUT_SEC = _cfg.get("stress_timeout_sec", 5)

# ─── LLM Providers ──────────────────────────────────────────────────────────
# Raw two-level dict from YAML: protocol → provider_name → config
LLM_PROVIDERS = _cfg.get("providers", {})
NOW_MODEL = _cfg.get("nowModel") or _cfg.get("now_model") or ""

# ─── Algorithm topics ────────────────────────────────────────────────────────
ALGO_TOPICS = _cfg.get("topics", {})


# ─── Helper functions ────────────────────────────────────────────────────────

def _format_provider(protocol: str, name: str) -> str:
    return f"{protocol}.{name}"


def get_provider(name: str | None = None) -> tuple[str, dict]:
    """
    Look up a provider by name. Returns (protocol, config) or raises.

    Accepted names:
      - None / ""         → use config.yaml nowModel
      - "deepseek"        → legacy provider-name lookup
      - "openai.deepseek" → explicit protocol.provider lookup
    """
    name = name or NOW_MODEL
    if not name:
        raise KeyError("No provider specified and config.yaml nowModel is empty")

    if "." in name:
        protocol, provider_name = name.split(".", 1)
        providers = LLM_PROVIDERS.get(protocol)
        if providers is None or provider_name not in providers:
            raise KeyError(f"Unknown provider: '{name}'")
        cfg = providers[provider_name]
        if not cfg.get("enabled", True):
            raise ValueError(f"Provider '{name}' is disabled in config.yaml")
        return protocol, cfg

    for protocol, providers in LLM_PROVIDERS.items():
        if name in providers:
            cfg = providers[name]
            if not cfg.get("enabled", True):
                raise ValueError(f"Provider '{name}' is disabled in config.yaml")
            return protocol, cfg
    raise KeyError(f"Unknown provider: '{name}'")


def list_enabled_providers() -> dict[str, tuple[str, dict]]:
    """Return {name: (protocol, config)} for all enabled providers."""
    result = {}
    for protocol, providers in LLM_PROVIDERS.items():
        for name, cfg in providers.items():
            if cfg.get("enabled", True):
                result[name] = (protocol, cfg)
    return result


def list_enabled_provider_choices() -> list[str]:
    """Return provider names accepted by the CLI, including protocol-qualified aliases."""
    choices = []
    for protocol, providers in LLM_PROVIDERS.items():
        for name, cfg in providers.items():
            if cfg.get("enabled", True):
                choices.append(name)
                choices.append(_format_provider(protocol, name))
    return sorted(set(choices))


def get_now_model() -> str:
    """Return the configured default provider reference."""
    return NOW_MODEL
