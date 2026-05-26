---
name: model-router
description: Intent-based model routing overlay for Hermes Agent. Use when a request should be mapped to a configured provider/model route such as image-prompt to Qwen 4B, debugging to Sonnet, cheap routine chat, or a user-defined route in skills.config.model-router.routes.
---

<!--
  IMPORTANT: This SKILL.md is a HERMES AGENT skill, NOT a Claude Code skill.
  Do NOT copy this directory into `~/.claude/skills/` or any Claude skill path.
  Copy this directory into the Hermes skills location on the machine running
  Hermes Agent (for example: `~/.hermes/skills/model-router/`).
  The surrounding `hermes-agent-specialist/` directory IS the Claude Code skill;
  this nested folder is one of its bundled assets that ships into Hermes.
-->

# Model Router for Hermes Agent

This Hermes skill adds **intent-based model-routing guidance** on top of stock Hermes. Hermes already supports `auxiliary.*`, `delegation.*`, `fallback_model`, custom providers, `/model`, and per-run `--provider --model` overrides. This skill does not add a Hermes core feature; it reads user-editable route settings from `skills.config.model-router` and returns the safest command or session-switch recommendation.

## Load the routing table

Read `~/.hermes/config.yaml` and inspect:

```yaml
skills:
  config:
    model-router:
      default_route: routine_chat
      execution_mode: advise_or_oneshot
      routes: {}
```

If the table is absent, ask the user to add the sample from `assets/config.yaml.routed`. Do not invent a root `intent_routes:` key.

## Route selection policy

Prefer native `auxiliary.*` slots for built-in fixed tasks. Use this skill only for semantic user intent. Match the user request against each route's `keywords` and `intent`. If multiple routes match, prefer the more specific and higher-capability route. If no route matches, use `default_route`.

## Execution policy

| `command_mode` | Behavior |
|---|---|
| `oneshot` | Build an isolated `hermes -z "..." --provider <provider> --model <model>` command. |
| `advise` | Recommend the exact `/model provider:model` or `hermes chat --provider ... --model ... -q ...` command. |
| `delegate` | Use Hermes delegation only when the task can be isolated as a subtask and the configured delegate model is appropriate. |
| `current_session` | Stay on the current/default session model. |

Always state selected route, provider, model, rationale, fallback route, and exact command. Never use `/model ... --global` unless the user explicitly asks to persist the change.

## Optional helper

When terminal access is available, run:

```bash
python scripts/model_router.py --prompt "<user request>" --config ~/.hermes/config.yaml
```

Use `--execute` only after the user confirms that an isolated `hermes -z` call is acceptable.
