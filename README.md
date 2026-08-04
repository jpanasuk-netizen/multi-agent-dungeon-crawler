# Multi-Agent Dungeon Crawler *(prototype)*

Local-LLM prototype where specialized agents collaborate to design and emit a playable dungeon campaign.

> **Honest label:** this is a **research / portfolio prototype**, not a production game engine.  
> It exists to show multi-agent task decomposition (systems design → level architecture → validation → playable HTML) on a personal GPU box.

[![Status](https://img.shields.io/badge/status-prototype-yellow)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue)]()
[![License](https://img.shields.io/badge/License-MIT-lightgrey)]()

---

## What you can do in 60 seconds

```bash
git clone https://github.com/jpanasuk-netizen/multi-agent-dungeon-crawler.git
cd multi-agent-dungeon-crawler

# already-generated campaign — no model required
xdg-open playable_dungeon.html   # or open in any browser
# also try: game.html , dungeon_viewer.html
```

Pre-built floors: `level_01.json` … `level_05.json`.

---

## Generate a new campaign (needs local Ollama)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export OLLAMA_URL=http://127.0.0.1:11434/api/generate
export DEFAULT_MODEL=qwen2.5:14b   # or any local instruct model

python3 run_pipeline.py
python3 generate_game.py
xdg-open playable_dungeon.html
```

---

## How the agents split work

| Agent | Job | Output |
|-------|-----|--------|
| **Systems** | Theme, player HP, enemy stats, loot rates scaled by floor | mechanics JSON |
| **Level Architect** | Place spawn, exit, walls, enemies, chests on an N×N grid | level JSON |
| **Validator** | Structural checks; feeds failures back for repair retries | accepted level or retry |

Details: [`ARCHITECTURE.md`](ARCHITECTURE.md).

```text
Concept → Systems Agent → Level Architect ⇄ Validator → level_0N.json → HTML player
```

---

## Repo contents

```text
multi-agent-dungeon-crawler/
├── README.md
├── ARCHITECTURE.md
├── run_pipeline.py          # agent orchestration
├── generate_game.py         # JSON levels → HTML
├── level_01.json … 05.json  # sample campaign
├── playable_dungeon.html
├── game.html
└── dungeon_viewer.html
```

No zip dumps. No mystery binaries. Source + sample outputs only.

---

## Context

Part of a broader independent year of local AI systems work:
- Infra/telemetry: [`local_grid_suite`](https://github.com/jpanasuk-netizen/local_grid_suite)
- Full private AI app stack: [`tabby-tavern-stack`](https://github.com/jpanasuk-netizen/tabby-tavern-stack)

## Author
Jeremy Panasuk · [@jpanasuk-netizen](https://github.com/jpanasuk-netizen)

## License
MIT
