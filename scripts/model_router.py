#!/usr/bin/env python3
"""Hermes model-router helper.

Reads skills.config.model-router.routes from a Hermes config YAML, selects a route
by keyword overlap, and prints a reversible Hermes command. It does not mutate
~/.hermes/config.yaml and never performs a global /model switch.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Run inside the Hermes Python environment or install pyyaml.") from exc


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Config root must be a mapping: {path}")
    return data


def router_cfg(config: Dict[str, Any]) -> Dict[str, Any]:
    return (((config.get("skills") or {}).get("config") or {}).get("model-router") or {})


def select_route(prompt: str, cfg: Dict[str, Any]) -> Tuple[str, Dict[str, Any], int]:
    routes = cfg.get("routes") or {}
    if not isinstance(routes, dict) or not routes:
        raise SystemExit("No routes found at skills.config.model-router.routes")
    text = prompt.lower()
    best_name = str(cfg.get("default_route") or next(iter(routes)))
    best_route = routes.get(best_name) or next(iter(routes.values()))
    best_score = -1
    for name, route in routes.items():
        if not isinstance(route, dict):
            continue
        score = 0
        for kw in route.get("keywords") or []:
            if str(kw).lower() in text:
                score += 3
        for word in str(route.get("intent") or "").lower().split():
            if len(word) > 4 and word.strip('.,:;()[]') in text:
                score += 1
        if score > best_score:
            best_name, best_route, best_score = str(name), route, score
    return best_name, best_route, best_score


def build_command(prompt: str, route: Dict[str, Any]) -> str:
    provider = route.get("provider")
    model = route.get("model")
    mode = route.get("command_mode") or "advise"
    if mode == "current_session" or not provider or not model:
        return "# Stay on the current Hermes session/default model."
    if mode == "oneshot":
        return " ".join(["hermes", "-z", shlex.quote(prompt), "--provider", shlex.quote(str(provider)), "--model", shlex.quote(str(model))])
    if mode == "delegate":
        return f"# Delegate as an isolated subtask if appropriate; configured target: provider={provider} model={model}"
    return f"/model {provider}:{model}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a Hermes model route from skills.config.model-router.routes")
    parser.add_argument("--prompt", required=True, help="User request to classify")
    parser.add_argument("--config", default=os.path.expanduser("~/.hermes/config.yaml"), help="Path to Hermes config.yaml")
    parser.add_argument("--execute", action="store_true", help="Execute only if selected route command_mode is oneshot")
    args = parser.parse_args()

    config = load_config(Path(args.config).expanduser())
    cfg = router_cfg(config)
    name, route, score = select_route(args.prompt, cfg)
    command = build_command(args.prompt, route)
    print(f"route: {name}")
    print(f"provider: {route.get('provider', '')}")
    print(f"model: {route.get('model', '')}")
    print(f"mode: {route.get('command_mode', 'advise')}")
    print(f"fallback_route: {route.get('fallback_route', '')}")
    print(f"rationale: {route.get('rationale', '')}")
    print(f"match_score: {score}")
    print(f"command: {command}")

    if args.execute:
        if route.get("command_mode") != "oneshot" or not command.startswith("hermes -z "):
            raise SystemExit("Refusing to execute: selected route is not command_mode=oneshot")
        return subprocess.call(command, shell=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
