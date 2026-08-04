# Architecture — Multi-Agent Dungeon Prototype

## Status
**Research prototype** (July 2026). Demonstrates agent-role decomposition for procedural content generation against a local LLM. Not a shipped game engine.

## Agent roles

```text
Concept
   │
   ▼
┌──────────────────┐
│  Systems Agent   │  → game mechanics JSON (HP, enemies, loot)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Level Architect │  → grid layout JSON (spawn/exit/walls/enemies/chests)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Validator loop  │  → structural checks + retry with failure feedback
└────────┬─────────┘
         ▼
 level_0N.json  →  generate_game.py  →  playable HTML
```

Implemented primarily in `run_pipeline.py`:
- `run_systems_agent` — mechanics schema via Ollama JSON mode
- `run_level_agent` — grid placement with repair feedback
- pathfinding / placement validation helpers
- floor scaling across 5 depths

## Runtime assumptions
- Local Ollama endpoint (`OLLAMA_URL`, default `http://127.0.0.1:11435/api/generate`)
- Default model env `DEFAULT_MODEL` (e.g. `qwen2.5:14b`)
- Offline play: pre-generated `level_0N.json` + static HTML viewers need no live model

## Deliverables in this repo
| Artifact | Purpose |
|----------|---------|
| `run_pipeline.py` | Multi-agent generation pipeline |
| `level_0N.json` | Five generated floors (checked in) |
| `generate_game.py` | Packs levels into HTML shell |
| `playable_dungeon.html` / `game.html` / `dungeon_viewer.html` | Browser play/view surfaces |

## Limits (intentional honesty)
- Single-node, prompt-programmed agents — not a durable orchestration framework
- No automated test suite / CI yet
- Combat/dialogue quality depends entirely on the local model
- Public packaging prioritizes clarity over claiming “engine” maturity
