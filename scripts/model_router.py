#!/usr/bin/env python3
"""Hermes model-router helper — Surf's up, dude.

Reads `skills.config.model-router.routes` from a Hermes config YAML, picks the
gnarliest route by keyword overlap, and prints a reversible Hermes command.
This script never paddles into `~/.hermes/config.yaml` to mutate it, and it
never pulls the cosmic emergency brake of a global `/model` switch. Strictly
catch-and-release routing, brah.
"""
from __future__ import annotations

# Standard-lib quiver. Lightweight on purpose — no heavy boards in shallow water.
import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

try:
    # PyYAML is the wax on this board. Without it, we ain't reading config.
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Run inside the Hermes Python environment or install pyyaml."
    ) from exc


def load_config(path: Path) -> Dict[str, Any]:
    """Paddle out, grab the YAML, hand it back as a dict. Wipe out cleanly on a bad path."""
    if not path.exists():
        # No board, no surf. Bail.
        raise SystemExit(f"Config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        # Root has to be a mapping. A list at the top is a kook move.
        raise SystemExit(f"Config root must be a mapping: {path}")
    return data


def router_cfg(config: Dict[str, Any]) -> Dict[str, Any]:
    """Dig through `skills.config.model-router` — the secret spot where the route table chills.

    Defensive `or {}` chain because any layer could be missing if the user
    hasn't dropped in the example block yet. We just shrug and return empty.
    """
    return (((config.get("skills") or {}).get("config") or {}).get("model-router") or {})


def select_route(prompt: str, cfg: Dict[str, Any]) -> Tuple[str, Dict[str, Any], int]:
    """Read the wave, pick the line. Returns (route_name, route_dict, score).

    Scoring is intentionally chill:
      - Each matching keyword: +3 (a solid set wave).
      - Each long word from `intent` that shows up in the prompt: +1 (ankle-slapper).

    Ties go to the first-declared route, so user route order in YAML matters —
    pop your priority routes up top, kook.
    """
    routes = cfg.get("routes") or {}
    if not isinstance(routes, dict) or not routes:
        # Empty lineup. No routes to ride.
        raise SystemExit("No routes found at skills.config.model-router.routes")

    text = prompt.lower()

    # Start with the user's declared default, or first route if no default set.
    # If literally nothing matches the prompt, we'll cruise back to this.
    best_name = str(cfg.get("default_route") or next(iter(routes)))
    best_route = routes.get(best_name) or next(iter(routes.values()))
    best_score = -1  # -1 so even a zero-score match beats the default. Fresh wax beats old wax.

    for name, route in routes.items():
        if not isinstance(route, dict):
            # Malformed route — skip it. Don't let a busted board wreck the heat.
            continue

        score = 0

        # Keywords are the bread-and-butter signal: deterministic, user-curated.
        for kw in route.get("keywords") or []:
            if str(kw).lower() in text:
                score += 3

        # Intent description gets a soft +1 per real word. Filters out short
        # noise words (<= 4 chars) and trims punctuation so "debugging," still
        # counts as a hit. Less precise than keywords, hence the cheaper weight.
        for word in str(route.get("intent") or "").lower().split():
            if len(word) > 4 and word.strip('.,:;()[]') in text:
                score += 1

        if score > best_score:
            best_name, best_route, best_score = str(name), route, score

    return best_name, best_route, best_score


def build_command(prompt: str, route: Dict[str, Any]) -> str:
    """Build the exact Hermes command for the chosen route. Four moods:

      - `current_session`  -> stay on the current board. No command needed.
      - `oneshot`          -> one isolated `hermes -z` ride. Globals untouched.
      - `delegate`         -> hand the wave to a delegate; advisory only.
      - `advise` (default) -> tell the human exactly which `/model` switch to flip.
    """
    provider = route.get("provider")
    model = route.get("model")
    mode = route.get("command_mode") or "advise"

    # No-op route, or missing target. Don't fabricate a command that won't ride.
    if mode == "current_session" or not provider or not model:
        return "# Stay on the current Hermes session/default model."

    if mode == "oneshot":
        # `shlex.quote` is the leash here — keeps shell metachars from wrecking the run.
        # We build the command as a list-joined string so the user can copy-paste verbatim
        # AND so `--execute` can hand it straight to a subshell below.
        return " ".join([
            "hermes", "-z", shlex.quote(prompt),
            "--provider", shlex.quote(str(provider)),
            "--model", shlex.quote(str(model)),
        ])

    if mode == "delegate":
        # Delegation in Hermes is its own beast (`delegation.*` config). We just
        # surface the target so the human can decide whether to drop it in.
        return f"# Delegate as an isolated subtask if appropriate; configured target: provider={provider} model={model}"

    # Default `advise` mode: tell the user the in-session switch. No --global,
    # ever, unless they explicitly ask for it themselves.
    return f"/model {provider}:{model}"


def main() -> int:
    """CLI entry. Surf check, route pick, command print, optional ride."""
    parser = argparse.ArgumentParser(
        description="Select a Hermes model route from skills.config.model-router.routes"
    )
    parser.add_argument("--prompt", required=True, help="User request to classify")
    parser.add_argument(
        "--config",
        default=os.path.expanduser("~/.hermes/config.yaml"),
        help="Path to Hermes config.yaml",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute only if selected route command_mode is oneshot",
    )
    args = parser.parse_args()

    # Load + classify. If either step bails, the SystemExit messages above
    # already explain what went sideways.
    config = load_config(Path(args.config).expanduser())
    cfg = router_cfg(config)
    name, route, score = select_route(args.prompt, cfg)
    command = build_command(args.prompt, route)

    # Print the full receipt. Humans (and Claude, when this runs from a skill)
    # need to see exactly what got picked and why — no silent rides.
    print(f"route: {name}")
    print(f"provider: {route.get('provider', '')}")
    print(f"model: {route.get('model', '')}")
    print(f"mode: {route.get('command_mode', 'advise')}")
    print(f"fallback_route: {route.get('fallback_route', '')}")
    print(f"rationale: {route.get('rationale', '')}")
    print(f"match_score: {score}")
    print(f"command: {command}")

    if args.execute:
        # Hard safety rail: we ONLY auto-run isolated `hermes -z` one-shots.
        # `advise`, `delegate`, and `current_session` are user-driven by design.
        # Anything else — refuse and let the human paddle it themselves.
        if route.get("command_mode") != "oneshot" or not command.startswith("hermes -z "):
            raise SystemExit("Refusing to execute: selected route is not command_mode=oneshot")
        # shell=True is fine here because every interpolated value passed through
        # shlex.quote in build_command. No raw user input touches the shell.
        return subprocess.call(command, shell=True)

    return 0


if __name__ == "__main__":
    # Cowabunga.
    sys.exit(main())
