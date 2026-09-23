# HINATA — Project → Product Roadmap

> **HINATA** — *Human-like Intelligent Nurturing Autonomous Tomodachi Architecture*
> A local, autonomous AI companion for the desktop. ひなた: a warm, sunlit place.

## Current state (v1.1.0 — "The Living Companion")

| Layer | Status |
|---|---|
| Brain (`hinata-omni`) | ✅ one model: text + vision + thinking, uncensored, 64K ctx, 5/5 gauntlet |
| Tools (16) | ✅ web search, **screen vision**, **semantic memory**, files, shell, python, KG, apps, system |
| RAG semantic memory | ✅ nomic-embed-text, cosine recall, auto-indexed, auto-context + tool |
| Knowledge Graph | ✅ weighted triples, decay, fact extraction |
| Memory | ✅ SQLite, persistent, session rotation |
| Streaming speech | ✅ sentence-chunked TTS while generating |
| Mood | ✅ persistent temperament w/ decay (`/api/mood`) |
| Proactivity | ✅ 3 triggers (idle, health, new session) |
| Persona | ✅ SOUL.md: thinking discipline, no-emoji law, intelligence protocol |
| Voice | ✅ en-US-AvaNeural, emoji-free speech, push-to-talk mic in overlay |
| Desktop overlay | ✅ taskbar-only wandering, floats above taskbar, tray, hotkey, offline-vendored JS |
| Security | ✅ AST sandbox, shell whitelist, WS origin+token auth, CORS lockdown |
| Reliability | ✅ hard agent timeout, overrun salvage + nudge retry, auto model warm-up |

## Known limits (honest list)

- Thinking-model latency variance: 11–140 s per turn depending on how much she deliberates (mitigated by budget + salvage + nudge; inherent to a 2B thinking model).
- Tool-result phrasing is sometimes awkward — she has the facts, phrasing wobbles at 2B scale.
- Ablated model ≠ guaranteed zero refusals; ablation reduces them, doesn't erase them.

## Product gap analysis — project → product

| # | Gap | Why it matters | Effort |
|---|---|---|---|
| 1 | **One-command install** | Users double-click; they don't `pip install` | 2-3 days |
| 2 | **First-run wizard** | model pull, persona pick, mic permission — guided | 2-3 days |
| 3 | **Crash-proofing & auto-restart** | a consumer product never shows a stack trace | 2 days |
| 4 | **Settings UI** | voice, mood sensitivity, tool permissions — no config files | 2-3 days |
| 5 | **Update mechanism** | ship v1.2 without `git pull` | 2 days |
| 6 | **Offline-first packaging proof** | vendored JS done; verify fully airgapped boot | 1 day |

## Release plan

### v1.2 — "She's a product" (distribution)
- [x] PyInstaller backend → `hinata-backend.exe` — **single file, brain included**: hinata-omni Q4_K_M GGUF + vision projector bundled inside the exe; auto-provisions into local Ollama on first boot (`backend/core/provision.py`)
- [x] GitHub Actions release workflow — tag `v*` triggers: frontend build → GGUF download → exe build → smoke test → GitHub Release with the exe attached (`.github/workflows/release.yml`)
- [x] Local build/doctor script — `python product/setup.py build|doctor`
- [ ] Electron builder → signed NSIS installer (exe currently launched via `start-hinata-desktop.bat`)
- [ ] First-run wizard UI: test voice → pick persona → done (model pull is already automatic)
- [ ] Auto-start with Windows (opt-in), crash reporter (local logs, never auto-sends)

### v1.3 — "She's aware" (depth)
- [ ] Mood-aware idle behaviors (sad → sits, excited → wanders more) tied to movement engine
- [ ] VRMA clip state machine (idle → curious → walk → sit)
- [ ] Whisper.cpp local ASR — fully offline voice input
- [ ] sqlite-vec upgrade for RAG (ANN index beyond 800-message window)
- [ ] Screen-vision proactive triggers (e.g., "you've been on that error screen a while")

### v2.0 — "She connects" (ecosystem)
- [ ] Plugin SDK: third-party tools as sandboxed folders
- [ ] Hermes native toolsets re-enabled behind feature flags (agent path is live)
- [ ] Multi-persona SOUL profiles selectable at setup
- [ ] Optional companion app (second screen / phone)

## Business framing (if desired)
- **Open-core**: local companion free; paid tier = premium personas, voice packs, plugin marketplace.
- **Privacy-first positioning**: "The companion that never phones home" — verifiable, airgap-friendly.
- All local deps are MIT/Apache — no licensing landmines.

## Non-goals
- No cloud brain, no accounts, no subscriptions required to function.
- No telemetry by default (opt-in crash reports only).
