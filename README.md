# RippleGuard

**Catch silent breakage before it happens.** RippleGuard is a VS Code extension that analyzes your codebase's dependency structure and git history, then warns you — automatically, on every save — which other functions and files might be affected by the change you just made.

Built for a 9,000+ participant hackathon in a tight time window, RippleGuard was developed primarily via AI coding agents (Gemini, Claude Opus) under close human review, with every phase hand-verified against known ground truth before being trusted or built upon.

---

## The Problem

When you (or an AI coding assistant) change a function, other functions elsewhere in the codebase that depend on it can silently break. Nothing crashes immediately — the breakage surfaces later, often far from the change, and tracking it down manually can take hours. This problem gets *worse*, not better, as more code is generated or edited by AI tools, because AI-assisted edits often touch code the developer hasn't fully internalized the surrounding context for.

RippleGuard closes that gap by watching every save and telling you, in seconds, exactly what else in your codebase might need a second look.

---

## Our Approach

RippleGuard is built on one core design principle: **the impact analysis itself must be fully deterministic.** No part of the "what breaks?" answer is left to an LLM to guess. Every warning RippleGuard shows is derived from two hard, verifiable signals:

1. **Static dependency structure** — who imports whom, and who calls whose functions, extracted directly from the source code's AST.
2. **Historical co-change patterns** — which files have actually tended to change together in past commits, mined from git history.

These two signals are combined into a severity score per affected file/function, with clear reason codes explaining *why* something was flagged (e.g. `direct_import`, `high_cochange_frequency`, `indirect_relationship`).

Only *after* this deterministic analysis is complete does an LLM (Groq) optionally step in — strictly to translate the already-computed reason codes and names into a one-sentence, plain-English explanation. The LLM is never given file contents, is never allowed to introduce new facts, and is never a required dependency: if it's unreachable, RippleGuard's core warnings are entirely unaffected.

This split was a deliberate rejection of the more "AI-flavored" alternative — asking an LLM to reason about whether a change breaks things. That approach would have been non-deterministic, harder to verify by hand, and risky to demo live to judges. Determinism first, LLM polish second.

### Explicitly rejected approaches

For transparency, a few tempting directions were considered and ruled out early:

- **True semantic breakage detection** (type-checking or running the affected code paths) — would require integrating a type-checker or test-runner per language; not buildable to a trustworthy standard in the available time.
- **Signature-change-only triggering** — considered, but rejected as partially redundant with existing TypeScript tooling, and unhelpful for plain JavaScript/Python users.
- **Test-suite-based breakage detection** — rejected because it only works on repos that already have well-written tests, which wouldn't reliably demo on an arbitrary judge's codebase.

---

## Architecture

```
Developer saves a file in VS Code
              |
              v
     VS Code Extension (TypeScript)
              |
              |  POST /api/analyze-function/
              v
        Django REST API
              |
              v
        Change Detector
   (diff old vs new content)
         |          |
         v          v
Function-Level    File-Level
Call Graph        Dependency Graph
(tree-sitter/ast)  (networkx)
         |          |
         |          v
         |     Co-change Miner
         |       (GitPython)
         |          |
         v          v
        Scoring Engine
 (graph distance + co-change frequency)
              |
     ---------+---------
     |                 |
     v                 v
  Groq API      Structured JSON Response
 (optional,             |
 plain-English)---------+
              |
              v
     VS Code Extension
              |
     ---------+---------
     |                 |
     v                 v
Popup Notification   Persistent Sidebar
                     (searchable history)
```

### Language support via a resolver interface

A core architectural bet — made early and validated later in Phase C — was that language-specific parsing logic should sit behind one abstract interface, so adding a new language never requires touching the graph builders, scoring, API, or extension.

```
             LanguageResolver (abstract)
             --------------------------
             + parse_file()
             + extract_imports()
             + extract_function_calls()
             + extract_function_definitions()
             + resolve_import_to_filepath()
                       |
            -----------+-----------
            |                     |
            v                     v
      JSTSResolver          PythonResolver
      --------------        ------------------------
      tree-sitter based     Python `ast` module based
      handles relative      handles relative dot imports,
      imports               sys.path, __init__.py packages
```

Both resolvers were verified against dedicated fixture repositories (`fixture_repo/` for JS/TS, `fixture_repo_python/` for Python), each hand-traced for expected node and edge counts before being trusted — the same rigor applied to every phase of this project.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Analysis engine | Python, tree-sitter, networkx, GitPython | AST-accurate parsing, graph algorithms, real git history mining |
| Backend API | Django + Django REST Framework, SQLite | Fast to stand up, clean error handling, simple deploy story |
| VS Code extension | TypeScript, VS Code Extension API | Native save hooks, Webview + WebviewView for UI |
| LLM layer | Groq API (free tier) | Fast inference, used *only* for optional plain-English explanations — never core logic |

---

## Features

### 1. On-save automatic impact analysis
Every save of a JS/TS or Python file triggers a background function-level diff against the last saved version. If the changed function has known callers, a notification fires immediately — with **no manual command required**.

### 2. Manual full-file analysis
`Ctrl+Shift+P` → **RippleGuard: Analyze Impact** — runs a broader file-level dependency analysis and shows results in a dedicated Webview panel.

### 3. Persistent, searchable impact history sidebar
A dedicated Activity Bar panel keeps a running, session-level log of every impact warning — not just a popup that disappears. Entries are grouped by the function that changed, sorted newest-first, and filterable live by function or file name.

**Example flow — developer saves `utils.js`, editing `generateId()`:**

```
Dev  ->  Save file
Dev  ->  VS Code Extension
VS Code Extension  ->  Django API : POST /api/analyze-function/
Django API  ->  Analysis Engine : detect_changed_functions()
Analysis Engine    : build call graph
Analysis Engine    : score affected callers
Analysis Engine  ->  Django API : affected_functions[] (file + severity)
Django API  ->  VS Code Extension : JSON response
VS Code Extension  ->  Dev : Popup - "Changing generateId() (utils.js)
                              may affect: createSession() in auth.js, ..."
VS Code Extension  ->  Dev : Sidebar entry appended (searchable, grouped)
```

### 4. Multi-language support
JavaScript, TypeScript, and Python are all supported through the same `LanguageResolver` interface described above — with correct, language-appropriate import resolution rules for each (not copy-pasted logic).

### 5. Optional AI-generated explanations
Each flagged file/function can carry a short, plain-English sentence explaining *why* it was flagged, generated by Groq from the already-computed reason codes only — grounded, non-hallucinated, and always safe to fall back to `null` if the API is unreachable or slow.

---

## Project Structure

```
RippleGuard/
├── engine/
│   ├── resolvers/
│   │   ├── base.py                  # Abstract LanguageResolver interface
│   │   ├── js_ts_resolver.py        # JS/TS implementation (tree-sitter)
│   │   └── python_resolver.py       # Python implementation (ast)
│   ├── graph_builder.py             # File-level dependency graph
│   ├── function_graph_builder.py    # Function-level call graph
│   ├── cochange_miner.py            # Git co-change history mining
│   ├── change_detector.py           # Diffs old vs. new function bodies
│   ├── function_analyzer.py         # Function-level orchestration
│   ├── analyzer.py                  # File-level orchestration
│   ├── scoring.py                   # Severity scoring math
│   └── groq_client.py               # Optional LLM explanation layer
├── extension/
│   └── rippleguard/
│       └── src/extension.ts         # VS Code extension (on-save + sidebar + manual command)
├── fixture_repo/                    # JS/TS test fixture (permanent, hand-verified)
├── fixture_repo_python/             # Python test fixture (permanent, hand-verified)
└── .env                             # GROQ_API_KEY (never committed — see below)
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js + npm
- Git
- VS Code

### 1. Clone and install backend dependencies
```bash
git clone https://github.com/<your-username>/RippleGuard.git
cd RippleGuard
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure the Groq API key (optional but recommended)
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_key_here
```
This file is git-ignored by default. RippleGuard runs perfectly well without it — explanations simply stay `null`.

### 3. Run the Django API
```bash
python manage.py runserver
```

### 4. Run the VS Code extension
```bash
cd extension/rippleguard
npm install
npm run compile
```
Then open the `extension/rippleguard` folder in VS Code and press `F5` to launch the Extension Development Host.

---

## Testing Philosophy

Every phase of this project was verified by hand before being trusted, using dedicated fixture repositories with known, traceable dependency structures — never assumed correct just because code compiled or ran without errors. Manual test scripts (`engine/manual_test_phase*.py`) reproduce this verification and can be re-run at any time to confirm no regressions were introduced by later phases.

---

## Known Limitations

- Notification/analysis granularity does not (and intentionally does not) attempt true semantic breakage detection — see *Explicitly rejected approaches* above.
- Import resolution handles common patterns (relative imports, `sys.path`, package `__init__.py` for Python) but not every possible module-resolution edge case (e.g. path aliases).
- No caching layer yet — every analysis re-parses files and re-walks git history from scratch.
- Session history in the sidebar is in-memory only and does not persist across VS Code restarts.

---

## Hackathon Context

Built under real time constraints, with a strict working process maintained throughout:
- One phase built and verified at a time — never combined.
- No code trusted or built upon until its output was hand-verified against known ground truth.
- No bare exception handling anywhere in the codebase.
- Fixture repositories treated as permanent, protected test data.
- A git commit after every verified-correct phase, with a clear commit message.

---


