# HINATA — Human-like Intelligent Nurturing Autonomous Tomodachi Architecture

*HINATA (ひなた) — a warm, sunlit place.*

A **local, autonomous AI companion** for your desktop. One multimodal brain (text + vision + thinking, uncensored), persistent memory with semantic recall, a living knowledge graph, real tool use, and an embodied VRM avatar who walks your taskbar. Zero cloud. Zero telemetry. Zero accounts.

```
        YOU ── voice / text ──►  HINATA
                                   │
                     ┌─────────────┴─────────────┐
                     │        BrainFeature       │
                     │  (agentic tool loop)      │
                     └──┬──────┬──────┬──────┬───┘
                        │      │      │      │
                   memory    RAG     KG    tools
                   (SQLite) (vectors)(triples)(16)
                        │      │      │      │
                     ┌──┴──────┴──────┴──────┴───┐
                     │  hinata-omni (Ollama)     │
                     │  Qwen3-VL-2B-Thinking     │
                     │  abliterated Q4_K_M 1.6GB │
                     └───────────────────────────┘
                                   │
                          VRM avatar · taskbar
```

## Features

- **One brain for everything** — `hinata-omni`: a single 2B vision-language model (Qwen3-VL-2B-Thinking, abliterated) that chats, reasons, *and sees your screen*. Runs fully inside a 6 GB GPU.
- **Agentic tool use** — 16 tools: live web search, screen vision, file I/O (sandboxed), shell (whitelisted), Python (AST sandbox), app launching, system monitoring, knowledge/memory operations. Multi-round tool loop with result feedback.
- **Semantic memory (RAG)** — every message embedded (`nomic-embed-text`, local) and recalled by meaning, not keywords. "What graphics card do I have?" finds the fact even if you never said "GPU".
- **Knowledge graph** — weighted entity/relation triples with time decay and reinforcement; a living model of what you told her, not a chat dump.
- **Personality & mood** — SOUL.md persona, 8-mood engine with real-time decay, mood-driven VRM expressions, proactive check-ins (idle, system health, new sessions).
- **Embodied avatar** — VRM via three-vrm; walks the taskbar (no pedestal), eyes track your cursor, breathes, gesture one-shots, lip-sync, mood expressions.
- **Voice** — neural TTS (`en-US-AvaNeural`), push-to-talk mic, emoji-free clean speech.
- **Streaming** — sentence-chunked speech starts while she's still thinking.
- **Private by architecture** — everything runs on your machine. No data leaves it.

## Quick Start

Requirements: **Windows**, **NVIDIA GPU (6 GB+ VRAM recommended)**, [Ollama](https://ollama.com), Python 3.11+, Node.js 18+.

```bash
# 1. Python deps
pip install -r requirements.txt

# 2. Build her brain (once) — model files in models-gguf/
cd models-gguf
ollama create hinata-omni -f Modelfile.omni
ollama pull nomic-embed-text
cd ..

# 3. Frontend (once)
cd frontend && npm install && npm run build && cd ..

# 4. Launch backend + desktop sprite
start-hinata-desktop.bat
```

She appears on your taskbar. Tray icon (orange sun) → Show/Hide, movement mode, open the React cortex. **Alt+Shift+H** summons/dismisses her. Hold the mic hotkey to talk.

Manual launch:

```bash
python -m uvicorn backend.main:app --port 8080   # brain
cd desktop-shell && npm start                     # sprite
```

## Configuration

Copy `.env.example` → `.env`. All knobs documented there: model names, agentic mode, tool-round budget, streaming, proactivity, auth token for the WS/REST API.

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — full system design, feature isolation, tool protocol
- [docs/PRODUCT.md](docs/PRODUCT.md) — product roadmap: project → installable product

## Repository Layout

```
backend/
  core/          event bus, SQLite, base feature, config, product metadata
  features/      brain · memory · rag · knowledge · mood · proactive · voice · tools · server
frontend/        React + Vite cortex (chat, mood chips, live KG panel)
desktop-shell/   Electron transparent overlay (VRM stage, tray, hotkeys)
gateway/         legacy WS bridge (hermes_brain)
hermes-agent/    vendored NousResearch Hermes agent (full toolsets available)
hermes-core/     SOUL.md — her persona
models-gguf/     Modelfiles + GGUF build inputs for hinata-omni
voice/           neural TTS engine
product/         PyInstaller spec + first-run setup (packaging)
docs/            architecture & product docs
```

## The Name

**HINATA** maps onto the architecture itself:

| Letter | Meaning |
|---|---|
| **H** | Human-like — personality, natural interaction |
| **I** | Intelligent — Hermes-grade reasoning and tool use |
| **N** | Nurturing — memory, relationship, emotional continuity |
| **A** | Autonomous — proactive, acts on her own |
| **T** | Tomodachi (友達) — friend |
| **A** | Architecture — the complete platform |

## License & Model Attribution

Code: this repository's license. Brain: [Qwen3-VL-2B-Thinking](https://huggingface.co/Qwen/Qwen3-VL-2B-Thinking) (Apache-2.0), abliterated variant by [huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-2B-Thinking-abliterated), GGUF quants by [mradermacher](https://huggingface.co/mradermacher/Huihui-Qwen3-VL-2B-Thinking-abliterated-GGUF). Hermes agent: [NousResearch](https://github.com/NousResearch/hermes-agent). TTS: Microsoft Edge neural voices via `edge-tts`.
