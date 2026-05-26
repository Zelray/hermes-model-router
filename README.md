# hermes-model-router

Intent-based model routing overlay for [Nous Research Hermes Agent](https://github.com/NousResearch/hermes-agent). A drop-in Hermes skill that maps semantic user intent (image-prompt writing, debugging, routine chat, plus any user-defined route) to a configured provider/model and emits the safest Hermes command — without mutating the global default model.

Targets **Hermes Agent 0.14.0**. Verify against your installed version with `hermes --version` before applying.

## What it does

Hermes already ships native fixed-task routing through `auxiliary.*`, `delegation.*`, `fallback_model`, custom providers, and per-run `--provider --model` overrides. Hermes does **not** ship a native arbitrary user-intent routing table. This skill adds that missing layer by:

1. Reading a user-editable route table from `skills.config.model-router.routes` in `~/.hermes/config.yaml`.
2. Classifying the active prompt against each route's `keywords` and `intent`.
3. Returning the exact `hermes -z`, `hermes chat`, or `/model` command for the selected route — never a silent global mutation.

## Flagship routes

| Route | Trigger phrases | Provider:model | Command mode |
|---|---|---|---|
| `image_prompt` | "image prompt", "midjourney", "flux", "sdxl", "stable diffusion" | `local-qwen:qwen3-4b` | `oneshot` (`hermes -z`) |
| `debugging` | "debug", "stack trace", "failing test", "traceback", "exception" | `openrouter:anthropic/claude-sonnet-4` | `advise` (`/model` or `hermes chat`) |
| `routine_chat` | (fallback) | `openrouter:openai/gpt-4o-mini` | `current_session` |

All routes are user-editable. Add your own under `skills.config.model-router.routes`.

## Install

1. Copy this directory into your Hermes skills location:
   ```bash
   cp -r hermes-model-router-skill ~/.hermes/skills/model-router
   ```
2. Merge the example route table from [`examples/config.yaml.routed`](./examples/config.yaml.routed) into `~/.hermes/config.yaml`.
3. Verify with `hermes config check` and `hermes doctor`.
4. Preload for a session: `hermes chat --skills model-router`.

## Usage

The skill is consumed automatically by Hermes when the user asks anything that matches a route's keywords or intent description. For deterministic dispatch from a script or shell wrapper:

```bash
python scripts/model_router.py --prompt "Write an image-generation prompt for a mechanical bee" \
  --config ~/.hermes/config.yaml
```

Outputs the selected route, provider, model, fallback, rationale, and the exact Hermes command. Append `--execute` to run isolated `command_mode: oneshot` commands automatically (other modes are refused).

## Configuration

See [`examples/config.yaml.routed`](./examples/config.yaml.routed) for the full annotated YAML.

```yaml
skills:
  config:
    model-router:
      default_route: routine_chat
      execution_mode: advise_or_oneshot
      routes:
        image_prompt:
          intent: "Write, refine, or translate a prompt for image generation."
          keywords: ["image prompt", "midjourney", "flux", "sdxl", "stable diffusion"]
          provider: local-qwen
          model: qwen3-4b
          command_mode: oneshot
          fallback_route: routine_chat
          rationale: "Cheap local small model is enough for prompt wording."
        debugging:
          intent: "Debug code, explain stack traces, diagnose failing tests."
          keywords: ["debug", "stack trace", "failing test", "traceback", "exception"]
          provider: openrouter
          model: anthropic/claude-sonnet-4
          command_mode: advise
          fallback_route: routine_chat
        routine_chat:
          intent: "Routine conversation and quick answers."
          provider: openrouter
          model: openai/gpt-4o-mini
          command_mode: current_session
```

## Route fields

| Field | Meaning |
|---|---|
| `intent` | Human-readable route description used by the classifier. |
| `keywords` | Deterministic match hints, scored higher than `intent` words. |
| `provider` | Hermes provider name (`openrouter`, `anthropic`, `lmstudio`, or a `custom_providers` entry). |
| `model` | Provider-specific model identifier — verify with `hermes model`. |
| `command_mode` | One of `oneshot`, `advise`, `delegate`, `current_session`. |
| `fallback_route` | Route to use if the selected provider/model is unavailable. |
| `rationale` | Cost/latency/capability explanation (docs only). |

## Safety

- Never runs `/model ... --global` unless the user explicitly asks to persist the change.
- The helper script refuses to execute anything that is not `command_mode: oneshot`.
- No writes to `~/.hermes/config.yaml`; the route table is user-owned config.
- All native Hermes failover (`fallback_model`) still applies underneath the overlay.

## Verification

Run the seven-row pre-flight checklist before relying on routes:

| Check | Command | Pass condition |
|---|---|---|
| Hermes starts | `hermes doctor` | No blocking errors |
| Providers configured | `hermes model` | Targets selectable |
| Config valid | `hermes config check` | No missing options |
| Config backed up | Copy `~/.hermes/config.yaml` | Rollback possible |
| Skill installed | Check `~/.hermes/skills/model-router/SKILL.md` | Path exists |
| Image route works | `hermes -z "image prompt for a mechanical bee" --provider local-qwen --model qwen3-4b` | Produces a prompt; global model unchanged |
| Debug route works | `/model openrouter:anthropic/claude-sonnet-4` | Session switches to Sonnet |

## Composio compatibility

This skill follows the [open agent skills standard](https://agentskills.io) (YAML frontmatter + Markdown + bundled scripts), which is interoperable with Composio's skill ingestion. To register with Composio, point at this repository root; the `SKILL.md` frontmatter is the source of truth for skill metadata.

## License

MIT — see [LICENSE](./LICENSE).

## Provenance

Derived from the `hermes-agent-specialist` Claude Code skill. All claims about native Hermes behavior are cross-checked against:

- [`NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent)
- [`cli-config.yaml.example`](https://github.com/NousResearch/hermes-agent/blob/main/cli-config.yaml.example)
- [`hermes_cli/config.py`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_cli/config.py)
- [Hermes Agent docs](https://hermes-agent.nousresearch.com/docs)
