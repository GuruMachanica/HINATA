# HINATA — Human-like Intelligent Nurturing Autonomous Tomodachi Architecture

<p align="center">
  <strong>ひなた — a warm, sunlit place.</strong><br/>
  A local autonomous desktop companion with one multimodal brain, persistent memory, semantic recall, a living knowledge graph, agentic tools, voice, and an embodied VRM avatar.
</p>

<p align="center">
  <a href="https://github.com/GuruMachanica/HINATA">Repository</a> ·
  <a href="docs/ARCHITECTURE.md">Architecture</a> ·
  <a href="docs/PRODUCT.md">Product Roadmap</a> ·
  <a href="https://github.com/GuruMachanica/HINATA/releases">Releases</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/HINATA-Local%20Autonomous%20AI-f59e0b?style=for-the-badge" alt="HINATA" />
  <img src="https://img.shields.io/badge/Windows-11%2B-141414?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-141414?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/React%20%2B%20Vite-Cortex-141414?style=for-the-badge&logo=react&logoColor=white" alt="React" />
  <img src="https://img.shields.io/badge/VRM-Embodied%20Companion-141414?style=for-the-badge" alt="VRM" />
  <img src="https://img.shields.io/badge/Privacy-Local%20First-141414?style=for-the-badge&logo=shield&logoColor=white" alt="Privacy" />
  <img src="https://img.shields.io/badge/Release-v1.2.0-141414?style=for-the-badge&logo=github&logoColor=white" alt="Release" />
</p>

---

## What is HINATA?

HINATA is a **fully local, autonomous AI companion for Windows**.

Instead of splitting chat, vision, memory, tools, voice, and the desktop avatar across unrelated services, HINATA composes them into one local system:

- **one multimodal model** for text, vision, and reasoning
- **agentic tools** with validation and risk levels
- **persistent conversation memory**
- **semantic RAG recall**
- **a weighted knowledge graph**
- **persistent mood and personality**
- **proactive background behavior**
- **streaming neural voice**
- **an embodied VRM desktop companion**
- **a bundled local inference engine for product builds**

The source repository is designed around local execution and local state.

## System Architecture

```text
                           YOU
                    voice / text / UI
                             │
                             ▼
              ┌──────────────────────────┐
              │       HINATA CORTEX      │
              │   FastAPI + Event Bus    │
              └────────────┬─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Brain            Memory / RAG       KG
     reasoning +       SQLite + vectors   triples
     tool loop               │                │
          │                   └──────┬─────────┘
          │                          │
          ├──────────────┐           │
          ▼              ▼           ▼
       16 Tools       Proactivity   Mood
       web / files /  idle / health persistent
       shell / python session       temperament
       vision / apps / system
          │
          ▼
   ┌────────────────────────────────────────┐
   │             LOCAL INFERENCE            │
   │                                        │
   │  hinata-omni                           │
   │  Qwen3-VL-2B-Thinking                  │
   │  abliterated · Q4_K_M + mmproj-Q8     │
   │  text + vision + thinking              │
   │                                        │
   │  Product build: bundled llama.cpp      │
   │  Vulkan engine                         │
   └────────────────────┬───────────────────┘
                        │
                        ▼
             ┌────────────────────┐
             │  DESKTOP SHELL     │
             │  Electron + VRM    │
             │  taskbar / tray    │
             │  hotkey / mic      │
             └────────────────────┘
```

## Key Capabilities

### One Brain for Everything

**`hinata-omni`** is the central multimodal model path: Qwen3-VL-2B-Thinking, using an abliterated GGUF build with a vision projector.

The same model handles:

- conversation
- reasoning
- screen understanding
- tool selection
- contextual replies

The documented architecture targets a **6 GB GPU class** machine.

### Agentic Tool System

HINATA exposes **16 tools** through a validated registry.

| Capability | Examples |
|---|---|
| Web | live web search |
| Vision | screenshot / screen understanding |
| Files | sandboxed file reads and writes |
| Shell | allowlisted commands |
| Python | AST-restricted execution |
| Apps | application launching |
| System | hardware / process / health inspection |
| Memory | conversation lookup and management |
| RAG | semantic retrieval |
| Knowledge | graph search and fact operations |

Each tool declares a **risk level**, validates parameters before execution, and isolates runtime failures.

### Semantic Memory

HINATA stores persistent conversation history in SQLite and can index messages into a vector store for semantic retrieval.

```text
message
   │
   ├── SQLite conversation store
   │
   └── local embedding
           │
           ▼
     vector in SQLite
           │
           ▼
   cosine similarity
           │
           ▼
   relevant past turns
```

Recall is available both automatically during context construction and through the semantic search tool.

### Living Knowledge Graph

Memory is not limited to chat transcripts.

HINATA extracts and reinforces **subject → relation → object** triples with confidence, source provenance, reinforcement weight, and temporal decay.

### Personality, Mood & Proactivity

HINATA has an explicit persona layer backed by `SOUL.md`, plus a persistent mood engine.

Background triggers include idle time, system health, and new sessions. Proactivity is bounded and configurable.

### Embodied Desktop Companion

The Electron desktop shell provides a transparent stage for a VRM avatar.

The companion can:

- wander along the taskbar
- track the cursor with her eyes
- breathe and idle
- play gesture one-shots
- change expressions from mood
- lip-sync to generated speech
- expose tray controls
- respond to **Alt+Shift+H**

### Streaming Voice

HINATA can synthesize speech with Microsoft Edge neural voices through `edge-tts`.

Streaming mode breaks generated replies into sentence-sized chunks so audio can begin while generation is still in progress.

Default voice:

```text
en-US-AvaNeural
```

## Brain Cycle

A normal cognition turn follows this path:

```text
USER QUERY
    │
    ▼
Context Builder
    │
    ├── recent conversation
    ├── related knowledge
    ├── semantic RAG hits
    └── persona / tool protocol
    │
    ▼
Reason + Act
    │
    ├── final response
    │
    └── {"tool": "...", "args": {...}}
              │
              ▼
         Tool Registry
              │
              ▼
         Tool Result
              │
              └───────► model
    │
    ▼
Reply Salvage
    │
    ├── clean internal artifacts
    ├── recover explicit conclusions
    └── nudge retry when thinking overruns
    │
    ▼
Learn
    │
    ├── memory.append
    ├── knowledge.observe
    └── hinata.spoke
```

### Why a custom tool loop?

HINATA keeps a lightweight hot path around **single local completions + explicit tool rounds**.

The vendored Hermes agent remains available, but the system does not force every turn through automatic continuation chains. This gives the small thinking model tighter control over latency and tool feedback.

## Model & Runtime

| Property | Current configuration |
|---|---|
| Primary model | Qwen3-VL-2B-Thinking |
| Variant | abliterated build |
| Main quant | Q4_K_M |
| Vision projector | mmproj-Q8 |
| Context | 65,536 tokens |
| Thinking budget | 1,200 tokens |
| Reference GPU | NVIDIA 6 GB class |
| Inference API | OpenAI-compatible local endpoint |
| Product engine | bundled llama.cpp / Vulkan |
| Fallback | Ollama-compatible endpoint |
| Embeddings | local embedding service |
| Backend | FastAPI |
| Frontend | React + Vite |
| Desktop | Electron |
| Avatar | VRM / three-vrm |
| TTS | edge-tts |

> The current product build bundles the local llama.cpp Vulkan engine and multimodal GGUF assets, removing the need for Ollama in the packaged backend.

## Current State — v1.2.0

| Layer | Status |
|---|---|
| Multimodal brain | ✅ text + vision + thinking |
| Agentic tools | ✅ 16 tools |
| Semantic memory | ✅ SQLite + embeddings + cosine recall |
| Knowledge graph | ✅ weighted triples + decay |
| Persistent memory | ✅ session-aware SQLite store |
| Streaming speech | ✅ sentence-chunked TTS |
| Mood | ✅ persistent temperament + decay |
| Proactivity | ✅ idle / health / session triggers |
| Persona | ✅ `SOUL.md` behavior layer |
| Desktop avatar | ✅ taskbar wandering VRM overlay |
| Security | ✅ tool risk model, shell allowlist, Python AST sandbox |
| Reliability | ✅ timeout, salvage, nudge retry, model warm-up |
| Product packaging | ✅ bundled backend build + release workflow |

## Honest Limits

HINATA is deliberately a small local-model system:

- thinking latency can vary with reasoning depth
- a 2B model can produce awkward phrasing on tool-result summaries
- an abliterated model can still refuse some requests
- semantic recall currently searches a bounded recent vector window rather than a full ANN index

## Security & Isolation

### Design laws

1. **≤125 LOC per source file**
2. **Features do not directly import each other** — cross-feature communication uses the typed event bus
3. **Everything is a plugin** — features, tools, and triggers register independently
4. **One shared SQLite database** — feature-owned tables with serialized writes

### Execution controls

- tool parameter validation
- `READ_ONLY`, `MUTATING`, and `DANGEROUS` risk levels
- sandboxed file operations
- allowlisted shell execution
- AST-restricted Python execution
- WebSocket origin validation
- optional `HINATA_AUTH_TOKEN`
- bounded REST parameters
- isolated tool dispatch
- serialized SQLite writes

## Repository Layout

```text
HINATA/
├── backend/
│   ├── core/
│   │   ├── event_bus.py          # cross-feature event transport
│   │   ├── database.py           # serialized SQLite access
│   │   ├── config.py             # runtime configuration
│   │   ├── engine_bootstrap.py   # bundled llama.cpp startup
│   │   ├── provision.py          # first-run model provisioning
│   │   └── base_feature.py       # feature registry
│   └── features/
│       ├── brain/                # cognition, tool loop, streaming
│       ├── memory/               # persistent conversations
│       ├── rag/                  # vector embeddings + recall
│       ├── knowledge/            # entity/relation graph
│       ├── mood/                 # temperament + decay
│       ├── proactive/            # background triggers
│       ├── voice/                # neural speech
│       ├── tools/                # tool abstraction + builtins
│       └── server/               # REST + WebSocket transport
├── engine/                       # local runtime support
├── frontend/                     # React + Vite cortex
├── desktop-shell/                # Electron transparent overlay
├── shell-bella/                  # desktop companion shell
├── hermes-agent/                 # vendored NousResearch agent
├── hermes-core/                  # persona / SOUL.md layer
├── models-gguf/                  # GGUF + Modelfile inputs
├── product/
│   ├── bundled-models/           # packaged model assets
│   ├── engine/                   # bundled llama.cpp runtime
│   ├── setup.py                  # build + doctor
│   └── hinata-backend.spec       # PyInstaller specification
├── docs/
│   ├── ARCHITECTURE.md           # deep technical design
│   └── PRODUCT.md                # project → product roadmap
├── gateway/                      # legacy WS bridge
├── shared/                       # shared assets / types
├── retired/                      # retired implementations
├── requirements.txt
├── start-hinata-desktop.bat
└── README.md
```

## Quick Start — Development

### Requirements

- Windows
- Python 3.11+
- Node.js 18+
- NVIDIA GPU with ~6 GB VRAM recommended

### 1. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare the development model

For the Ollama-compatible development path:

```bash
cd models-gguf
ollama create hinata-omni -f Modelfile.omni
ollama pull nomic-embed-text
cd ..
```

### 3. Build the React cortex

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Launch HINATA

```bash
start-hinata-desktop.bat
```

The launcher starts the FastAPI brain, waits for the backend, and then launches the Electron shell.

### Product build

```bash
python product/setup.py doctor
python product/setup.py build
```

Release builds are automated through GitHub Actions on `v*` tags.

## Configuration

Copy:

```text
.env.example → .env
```

Important settings:

```text
HINATA_MODEL_ENDPOINT
HINATA_MODEL_NAME
HINATA_VISION_MODEL
HINATA_AGENTIC
HINATA_MAX_TOOL_ROUNDS
HINATA_THINK_BUDGET
HINATA_STREAM
HINATA_STREAM_MIN_CHARS
HINATA_PROACTIVE
HINATA_PROACTIVE_INTERVAL
HINATA_PORT
HINATA_LOG_LEVEL
HINATA_AUTH_TOKEN
```

## Documentation

- [Architecture → `docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [Product roadmap → `docs/PRODUCT.md`](docs/PRODUCT.md)

## Product Direction

### v1.2 — Distribution

- packaged backend
- bundled local brain
- automated release build
- first-run setup
- installer and product UX hardening

### v1.3 — Awareness

- richer mood-driven animation states
- fully local ASR
- improved vector indexing
- proactive screen awareness

### v2.0 — Ecosystem

- plugin SDK
- selectable persona profiles
- optional companion device integration
- broader native toolsets behind feature flags

## The Name

| Letter | Meaning |
|---|---|
| **H** | **Human-like** — personality and natural interaction |
| **I** | **Intelligent** — reasoning and tool use |
| **N** | **Nurturing** — memory and emotional continuity |
| **A** | **Autonomous** — proactive behavior |
| **T** | **Tomodachi (友達)** — friend |
| **A** | **Architecture** — the complete platform |

## Dependencies & Attribution

| Component | Source |
|---|---|
| Primary model | [Qwen3-VL-2B-Thinking](https://huggingface.co/Qwen/Qwen3-VL-2B-Thinking) |
| Abliterated variant | [huihui-ai](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-2B-Thinking-abliterated) |
| GGUF quantizations | [mradermacher](https://huggingface.co/mradermacher/Huihui-Qwen3-VL-2B-Thinking-abliterated-GGUF) |
| Agent framework | [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent) |
| Local runtime | [llama.cpp](https://github.com/ggml-org/llama.cpp) |
| Avatar runtime | [three-vrm](https://github.com/pixiv/three-vrm) |
| Speech | [edge-tts](https://github.com/rany2/edge-tts) |

Model and dependency licenses remain governed by their upstream projects; the repository's own source license is separate.

## License

**PROPRIETARY — STRICT PRIVATE USE & INSPECTION LICENSE**

Copyright (c) 2026 Mohammad Huzaifa. All rights reserved.

Permission is granted solely for private educational study, personal learning, and peer inspection. Execution, deployment, copying, redistribution, derivative works, commercial exploitation, unauthorized AI training, and unauthorized academic submission are prohibited without prior written authorization.

See [LICENSE](LICENSE) for the complete terms, including third-party material exclusions and attribution requirements.

---

<p align="center">
  <strong>HINATA is not a cloud chatbot.</strong><br/>
  She is a local system: brain, memory, tools, voice, mood, and presence — living on your machine.
</p>
