# Python Code Review — Nebula Backend (`backend/app/`)

Reviewed: all 23 Python files under `backend/app/` (no git repo present, so this covers the full tree, not a diff).
Tools used: `ruff check`, `mypy`, `bandit`, `python -m ast`, plus manual read-through.

**Overall recommendation: FAIL / BLOCK** — the app cannot ingest a single document in its current state (see CRITICAL #1).

---

## CRITICAL

### 1. Syntax error makes the entire ingestion/RAG engine unimportable
**File:** `backend/app/pageindex_engine/utils.py:111`

```python
async def ChatGPT_API_async(model, prompt, api_key=None):
    max_retries = 10
    messages = [{"role": "user", "content": prompt}]
    for i in range(max_retries):
        try:
            client = get_async_client()
            response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0,
                )
                return response.choices[0].message.content   # <-- over-indented, SyntaxError
        except Exception as e:
            ...
```

`return` on line 111 is indented one level deeper than the `response = await ...` statement it follows. Confirmed via `python -m ast`:
```
IndentationError: unexpected indent
```

`page_index.py:7` does `from .utils import *` unconditionally (no try/except), so importing `page_index.py` — and therefore `rag/engine.py`, which `process_document()` calls for every file type — raises immediately. **Every document upload (PDF/MD/TXT/DOCX) currently fails.**

`page_index_md.py:5-8` wraps its own `from .utils import *` in a bare `except:` that falls back to `from utils import *` (no relative dot), which also fails since there's no top-level `utils` module — so the fallback doesn't save it either.

**Fix:** Dedent line 111 to align with `response = await client.chat.completions.create(...)`. Add a smoke test that just does `import app.pageindex_engine.page_index_md` and `import app.pageindex_engine.page_index` so this class of failure is caught in CI.

---

### 2. SSRF in URL ingestion — no host/scheme validation, redirects followed blindly
**Files:** `backend/app/ingestion/web.py:5-16`, `backend/app/api/documents.py:129-149`, `backend/app/models.py:43-46`

```python
async def fetch_url_to_markdown(url: str) -> tuple[str, str]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        response = await client.get(url)   # url passed straight through, no validation
```

`UrlIngestRequest.url` is a bare `str` (no `HttpUrl`, no scheme allow-list). The URL is fetched with `follow_redirects=True` and no re-validation of resolved hosts, so a user can make the backend fetch:
- cloud metadata endpoints (`http://169.254.169.254/latest/meta-data/...`, `metadata.google.internal`)
- internal/private network services (`127.0.0.1`, `10.x.x.x`, `192.168.x.x`)
- a public URL that 302-redirects to an internal address (redirect targets aren't re-validated)

The fetched content and title are then stored and served back as a "document" — SSRF-to-data-exfiltration.

**Fix:**
1. In `models.py`, restrict `url` to `http`/`https` scheme (e.g. `AnyHttpUrl` or a custom validator).
2. In `web.py`, before connecting, resolve the hostname and reject loopback/private/link-local/reserved ranges (`ipaddress.ip_address(...).is_private/is_loopback/is_link_local/is_reserved`). Re-check on every redirect hop — set `follow_redirects=False` and manually validate each `Location` header before following, or use an `httpx` event hook.
3. Explicitly block `169.254.169.254` and deny `.local`/`.internal` suffixes.
4. Add a response size cap (currently only a 10s timeout; no cap on streamed bytes).

---

## HIGH

### 3. CORS wildcard origin + credentials
**File:** `backend/app/main.py:38-45`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```
Starlette's `CORSMiddleware` reflects the request's `Origin` verbatim (not a literal `*`) whenever `allow_credentials=True` is combined with a wildcard, while still sending `Access-Control-Allow-Credentials: true`. Any origin can make credentialed cross-site requests. Not exploitable today (no cookie/session auth yet), but becomes a full cross-site data exposure the moment auth is added — fix now.

**Fix:** Set `allow_origins` to an explicit configured list (e.g. via a `CORS_ORIGINS` setting), or set `allow_credentials=False` if auth stays purely bearer-token based.

### 4. Agent nodes hardcode `model="phi3"`, ignoring `settings.LLM_MODEL`
**File:** `backend/app/agent/graph.py:34, 90, 121, 145`

All four LangGraph nodes (`plan_node`, `write_node`, `grade_documents`, `rewrite_plan`) call `client.chat.completions.create(model="phi3", ...)` with a hardcoded literal, while `rag/engine.py:37` correctly uses `settings.LLM_MODEL`. The comment `# Usually overriden by base_url model` is incorrect — `model` is sent verbatim in the request body regardless of `base_url`. Any deployment configured for OpenAI or another provider will get a hard error on every chat turn.

**Fix:** Replace all four literals with `settings.LLM_MODEL` (`from app.config import settings`).

### 5. `grade_documents` fails open
**File:** `backend/app/agent/graph.py:135-137`
```python
except Exception as e:
    print(f"Grade error: {e}")
    return {"documents_relevant": "yes", "iteration_count": ...}
```
On any exception (timeout, malformed response, provider outage) the grader declares the context relevant and proceeds to `write_node`, silently degrading answer quality instead of surfacing the failure or retrying.

**Fix:** Fail closed — return `"no"` or propagate the error so the caller can distinguish "no relevant docs" from "grading broke."

### 6. Long-held DB transaction spans unbounded external I/O in chat endpoint
**File:** `backend/app/api/chat.py:160-230`

The `async with get_db() as db:` block inserts the user message (uncommitted), then calls `await graph.ainvoke(initial_state)` — several sequential LLM HTTP calls (plan → fetch → grade → possibly rewrite → write) — and only commits after the assistant reply is generated. SQLite is in WAL mode with a single-writer model, so this holds an open write transaction across unbounded network I/O: concurrent writes (a second chat message, a document status update) will hit `SQLITE_BUSY` for the full LLM round-trip duration. It's also a data-loss bug — if the process crashes before the final `commit()`, the user's message is silently rolled back even though they believe it was sent.

**Fix:** Commit the user message in its own short transaction, close that connection, run `graph.ainvoke` with no DB connection held open, then open a second short transaction to persist the assistant response.

### 7. Broad exception handling swallows errors with `print()` instead of `logging`
**Files:** `agent/graph.py:55-57, 104-106, 135-137, 163-165`, `api/chat.py:197-201`, `rag/engine.py:94-98`

Every LLM call in the agent graph is wrapped in `except Exception as e: print(f"... error: {e}")` — discards the traceback, bypasses log aggregation, and returns a degraded-but-successful-looking state. `rag/engine.py:97` (`except Exception: continue`) silently skips any document whose `tree.json` fails to parse — no signal to the user or logs.

**Fix:** Replace all `print(...)` with `logging.getLogger(__name__).exception(...)`. Reserve broad `except Exception` only at the outermost node boundary.

### 8. Mutable default argument
**File:** `backend/app/pageindex_engine/utils.py:504`
```python
def remove_fields(data, fields=['text']):
```
Not actively broken today (the function doesn't mutate the list), but a latent trap for the next contributor.

**Fix:** `def remove_fields(data, fields=None): fields = fields if fields is not None else ["text"]`

### 9. Bare `except:` clauses hide the real failure
**Files:** `pageindex_engine/page_index_md.py:7`, `pageindex_engine/utils.py:162`

`page_index_md.py:5-8`'s bare `except:` is catching the SyntaxError from CRITICAL #1 and masking it with an import fallback that itself fails — exactly why the module-breaking bug wasn't caught earlier. `utils.py:158-163`'s bare `except:` inside `extract_json`'s cleanup path hides any error other than the one JSON-decode case it's meant to handle.

**Fix:** Catch specific exceptions (`ImportError`, `json.JSONDecodeError`) and log what was caught.

### 10. Missing type hints across the PageIndex engine
**Files:** `pageindex_engine/utils.py` (nearly every function), `pageindex_engine/page_index.py`, `pageindex_engine/page_index_md.py`

None of the ~40 public functions in this package have type annotations, unlike the rest of the app. `mypy` can't check this module beyond syntax — and it's the module doing the most I/O/JSON/LLM-response parsing in the codebase.

**Fix:** At minimum annotate the entry points consumed by `rag/engine.py`: `page_index_main`, `md_to_tree`, `ConfigLoader.load`, `get_leaf_nodes`.

---

## MEDIUM

- **Duplicate code** between `upload_document` and `ingest_url` (`api/documents.py:91-126` and `163-198`) — extract a shared `_create_document_record(...)` helper.
- **`get_document_tree` has no DB/ownership check** (`api/documents.py:265-273`) — unlike every other endpoint, goes straight from path params to filesystem with no notebook/document existence check or UUID format validation.
- **`build_graph()` recompiled on every chat message** (`api/chat.py:179`) — compile once at module import time instead.
- **Unsafe direct dict-key access** on LLM-adjacent data (`agent/graph.py:83-84, 112`) — `ctx['source_filename']` etc. use `[]` instead of `.get(...)`, risking unhandled `KeyError`.
- **Inconsistent return type on retry-exhaustion path** (`pageindex_engine/utils.py:40-68`, `ChatGPT_API_with_finish_reason`) — normal path returns a 2-tuple, exhausted-retries path returns a bare string `"Error"`, causing `ValueError: not enough values to unpack` for callers doing `content, reason = ...`.
- **Shadowing the `list` builtin** (`pageindex_engine/utils.py:545`, `check_token_limit`) — rename `list = structure_to_list(structure)` to `nodes = ...`.
- **`ruff` findings (auto-fixable):** unused imports (`api/chat.py:9`, `api/documents.py:7`, `ingestion/pipeline.py:7`, `rag/engine.py:7`); E402 imports-after-code in `agent/graph.py:24-27`; `from .utils import *` (F403) in `page_index.py:7`, `page_index_md.py:6,8`; F541 f-strings without placeholders in `page_index_md.py:247,250,255,258,264,270,278`.
- **Magic numbers without named constants:** `max_retries = 10`, `time.sleep(1)`, `summary_token_threshold=200`, `limit=110000`, `results[:5]` top-k (`rag/engine.py:120`), `timeout=10.0` (`ingestion/web.py:13`), `iteration_count >= 3` repeated in `agent/graph.py:72,174` without a shared constant.
- **Non-idiomatic index loops** instead of direct iteration (`pageindex_engine/utils.py:262-264, 276-282, 429-433`).
- **`print()` used for logging** in production code paths (`pageindex_engine/utils.py:512-530`, `pageindex_engine/page_index.py:911`).
- **Unsanitized webpage title used as stored filename/metadata** (`api/documents.py:151`, source `ingestion/web.py:21`) — only `.strip()` applied to the fetched `<title>`; sanitize/truncate before persisting.

---

## Checked and NOT flagged
- `bandit` B311 (`random.sample` in `page_index.py:912`) — non-cryptographic sampling for a QA-check helper, not a finding.
- `ConfigLoader._load_yaml` (`utils.py:698-701`) correctly uses `yaml.safe_load`, not `yaml.load`.
- All SQL in `api/notebooks.py`, `api/chat.py`, `api/documents.py`, `database.py` uses parameterized `?` placeholders — no SQL injection.
- No hardcoded secrets found; API keys are sourced from environment via `pydantic-settings`.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 2 |
| HIGH | 8 |
| MEDIUM | 11 |

Fix order suggested: #1 (syntax error, one-line fix) → #2 (SSRF) → #3 (CORS) → #4 (hardcoded model) → rest.
