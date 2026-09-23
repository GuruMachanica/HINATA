# HINATA — System Architecture

## Design Laws

1. **≤125 lines of code per file.** Any file that outgrows this is split into focused sub-modules. Enforced by sweep in CI habits.
2. **Features never import each other.** All cross-feature communication flows through a typed event bus (`core/event_bus.py`). A crash in one subscriber can never take down another feature.
3. **Everything is a plugin.** Features subclass `BaseFeature` + `@register`; tools subclass `Tool`; triggers subclass `Trigger`. Adding one means adding a file — nothing else changes.
4. **One shared SQLite, feature-scoped tables.** Writes go through a serialized transaction helper (`core/database.py`).

## Process Topology

```
┌─ desktop-shell (Electron) ─────────────────────────┐
│  transparent always-on-top overlay, floats ABOVE   │
│  taskbar · VRM stage (three-vrm, vendored offline) │
│  mic push-to-talk · tray · Alt+Shift+H hotkey      │
│  renderer errors forwarded to terminal             │
└──────────────┬─────────────────────────────────────┘
               │ WebSocket /ws  ·  REST /api/*   (CORS: localhost + null)
┌──────────────▼─────────────────────────────────────┐
│  backend (FastAPI, ONE Python process)             │
│                                                    │
│  main.py — bootstrap only: import features →       │
│  setup_all() → wire proactive → warm model         │
│                                                    │
│  core/            event bus · db · config ·        │
│                   base_feature registry · product  │
│                                                    │
│  features/                                         │
│   brain/      persona · context_builder ·          │
│               completion_client · hermes_engine ·  │
│               tool_loop · tool_parser ·            │
│               streaming_reply · stream_chunker ·   │
│               reply_salvage · turn_timeout ·       │
│               warmup · feature                     │
│   memory/     store (sessions, turns) · feature    │
│   rag/        vector_store (embeddings+cosine) ·   │
│               feature                              │
│   knowledge/  extractor · graph_store · kg_schema  │
│   mood/       decay (persistent temperament)       │
│   proactive/  triggers (idle/health/session) ·     │
│               engine                               │
│   voice/      synthesizer (edge-tts, LRU cache)    │
│   tools/      base · registry · builtin/           │
│               (system, files, shell, python,       │
│                web, vision, rag, memory, apps)     │
│   server/     state · ws_handler · rest · feature  │
└──────────────┬─────────────────────────────────────┘
               │ HTTP (OpenAI-compatible)
┌──────────────▼─────────────────────────────────────┐
│  Ollama                                            │
│   hinata-omni      Qwen3-VL-2B-Thinking abliterated│
│                    Q4_K_M + mmproj-Q8 · 64K ctx    │
│                    text + vision + thinking        │
│   nomic-embed-text 274 MB · RAG embeddings         │
└────────────────────────────────────────────────────┘
```

## The Brain Cycle

`BrainFeature.think(query)` runs one serialized cognition cycle:

1. **Context** (`context_builder`): recent conversation + KG associations + **RAG semantic hits**, assembled under the persona (SOUL.md) and tool protocol.
2. **Reason + act** (`tool_loop`): up to `HINATA_MAX_TOOL_ROUNDS` rounds. The model replies either with `{"tool": ..., "args": {...}}` JSON (executed, result fed back) or final prose. Runs on **single completions** (`chat_raw`) — the most reliable path on a 2B thinking model.
3. **Salvage** (`reply_salvage`): strips mood tag, emojis, stage directions; if thinking overran the budget, extracts only an explicitly stated conclusion; else a nudge retry asks for an immediate answer.
4. **Learn**: emits `memory.append` (→ indexed into RAG), `knowledge.observe` (KG triples), `hinata.spoke` (mood + avatar).

### Engine paths

| Path | Use | Notes |
|---|---|---|
| `chat_raw` | tool loop (hot path) | single completion + nudge retry; most reliable |
| `chat` | full agent power | vendored Hermes `AIAgent` with native toolsets, hard 90 s timeout (`turn_timeout` — daemon thread, never blocks on exit) |
| `chat_stream` | streaming replies | SSE deltas, cleaned per-chunk |

### Why the Hermes agent is not the hot path

The 2B thinking model occasionally overruns its reasoning budget; Hermes' auto-continuation then chains long requests and can confabulate. Single completions + our own loop + salvage/nudge layers give deterministic behavior while the full agent remains available (64 K context satisfies its minimum) for future toolset-native work.

## RAG (Semantic Memory)

- `nomic-embed-text` (274 MB, local) embeds every stored message (768-d).
- Vectors live in SQLite (`embeddings` table, packed floats).
- Recall = cosine similarity over recent vectors, top-k with a 0.35 floor.
- Served two ways: automatically in context (`Semantically related past conversation:`) and as the `semantic_search` tool.
- Failures are non-blocking: if the embed endpoint is down, recall returns empty and everything else works.

## Vision

`see_screen` captures a monitor (`mss`), downscales to JPEG, and sends it with the question to `hinata-omni`'s vision projector (mmproj-Q8). The same model answers — one brain for text and sight.

## Model Card

| Property | Value |
|---|---|
| Model | Qwen3-VL-2B-Thinking (abliterated by huihui-ai) |
| Quant | Q4_K_M (1.06 GB) + mmproj Q8_0 (445 MB) |
| Context | 65,536 tokens (Hermes-compatible) |
| Sampling | temp 0.5 · top_k 20 · top_p 0.95 · repeat 1.2 · presence 1.5 |
| VRAM | ~3.9 GB resident (4050 6 GB, zero CPU spill) |
| Speed | ~20–40 tok/s thinking, faster prose |

## Isolation & Safety

- Tool risk levels; `write_file` path-sandboxed; `run_shell` allowlisted; `run_python` AST-whitelisted sandbox.
- WS origin validation + optional `HINATA_AUTH_TOKEN`; CORS limited to localhost/null.
- Every bus subscriber and tool dispatch is exception-wrapped: a failure logs and the system continues.
