# HINATA — Human-like Intelligent Nurturing Autonomous Tomodachi Architecture

*HINATA (ひなた) — a warm, sunlit place.* A local, autonomous AI companion for the desktop:
genuinely agentic brain, persistent memory, a living knowledge graph, and an embodied
VRM avatar with procedural lifelike motion.

## Architecture (v2 — FastAPI + React)

```
┌─ frontend (React + Vite, built to dist/) ──────────────┐
│  VRM avatar stage (three-vrm, procedural poses)        │
│  chat feed · mood chips · live Knowledge Graph panel   │
└────────────────────┬───────────────────────────────────┘
                     │ WebSocket /ws  +  REST /api/*
┌────────────────────▼───────────────────────────────────┐
│ backend/ — FastAPI (ONE Python process)                │
│  main.py     WS protocol + REST + static serving       │
│  brain.py    real Hermes AIAgent → Ollama hinata-brain │
│  memory.py   SQLite conversation memory (persistent)   │
│  kg.py       Knowledge Graph: triples, weight decay,   │
│              fact extraction, entity co-occurrence     │
│  voice/      edge-tts neural synthesis (AriaNeural)    │
└────────────────────┬───────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────┐
│ desktop-shell/ (Electron)                              │
│  transparent always-on-top overlay · tray · hotkey     │
│  Alt+Shift+H · wander/follow-cursor movement engine    │
│  click-through except on her · spring-bone wind        │
└────────────────────────────────────────────────────────┘
```

## What HINATA is now

| Capability | Implementation |
|---|---|
| **Brain** | Real NousResearch Hermes `AIAgent` (vendor/hermes-agent) → local Ollama `hinata-brain` (heretic Qwen-3-VL 2B GGUF). Zero cloud. |
| **Memory** | SQLite rolling conversation history, auto session rotation, keyword recall — she remembers yesterday. |
| **Knowledge Graph** | Every turn extracts entities + explicit facts ("my GPU is...", "I'm building...") into weighted triples. Reinforces on repetition, decays over time, injects into prompts. She answers "what GPU do I have?" from the graph. |
| **Mood** | Bella-style mood tag on every reply → VRM expression + behavior. |
| **Body** | Procedural pose engine (ported from liqu): breathing, weight-shift, micro-motion, walk/sit/wave/think/stretch, spring-bone wind, cursor gaze, blink, amplitude lip-sync. |
| **Desktop presence** | Electron transparent overlay: she walks the screen edges, follows your cursor, click-through except on her, tray + `Alt+Shift+H`. |
| **Voice** | edge-tts AriaNeural via `/api/tts`, audio streamed for lip-sync. |

## Run

```powershell
# 1. Ollama with the brain model
ollama run hinata-brain

# 2. Backend (serves API + built React UI on one port)
pip install fastapi "uvicorn[standard]"
python -m uvicorn backend.main:app --port 8080

# 3a. Browser cortex
open http://127.0.0.1:8080

# 3b. Desktop overlay
cd desktop-shell && npm install && npm start
# or double-click start-hinata-desktop.bat for both
```

### Rebuild the frontend after changes

```powershell
cd frontend && npm install && npm run build
```

## API surface

| Endpoint | Purpose |
|---|---|
| `WS /ws` | chat, agent state, mood, TTS audio, kg_update events |
| `GET /api/health` | liveness + memory + KG stats |
| `GET /api/kg/graph?limit=` | full graph for visualization |
| `GET /api/kg/related?entity=` | neighbors of an entity |
| `GET /api/kg/facts` | explicit facts she learned about you |
| `GET /api/kg/search?term=` | triple search |
| `GET /api/memory/recent` | recent conversation turns |
| `GET /api/memory/search?term=` | recall past conversations |
| `GET /api/tts?text=` | text → MP3 audio |

## Repo layout

```text
HINATA/
├── backend/            # FastAPI: brain, memory, KG, WS/REST (one process)
├── frontend/           # React + Vite source (builds to dist/)
├── desktop-shell/      # Electron transparent overlay
├── hermes-agent/       # NousResearch engine (the brain's runtime)
├── hermes-core/        # Persona (SOUL.md) + retained proactive/diagnostics modules
├── voice/              # edge-tts neural synthesis
├── models-gguf/        # Modelfile for hinata-brain (heretic Qwen-3-VL)
└── retired/            # bella, arpa-avatar, hanami, liqu — heritage & reference codebases
```

## Credits

Built on the shoulders of: [NousResearch hermes-agent](https://github.com/NousResearch/hermes-agent)
(brain), [Jackywine/Bella](https://github.com/Jackywine/Bella) (mood DNA),
[ARPAHLS/avatar](https://github.com/ARPAHLS/avatar) (VRM pipeline),
[Undi95/Hanami](https://github.com/Undi95/Hanami) (animation stack),
[CameronCodesStuff/liqu-companion](https://github.com/CameronCodesStuff/liqu-companion)
(desktop overlay + procedural motion). All merged and reimplemented for HINATA.
