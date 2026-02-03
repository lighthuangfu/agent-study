## Quick orientation for AI coding agents

This repo is a small LangGraph-based agent template. Below are focused, actionable notes to help code and edit with minimal setup.

### Big picture (files to read first)
- `src/agent/graph.py` — constructs a `StateGraph` and compiles it to `graph`. The graph wires three nodes: `weather_expert`, `rss_expert`, and `aggregator`.
- `src/agent/nodes.py` — implementations of graph nodes. Key behaviors:
  - Nodes return dicts with keys matching the `AgentState` TypedDict in `src/agent/states.py`.
  - `aggregator_node` must return `{"messages": [AIMessage(...)]}` so invocations contain `content`.
  - Nodes use `create_react_agent(_llm, ALL_TOOLS)` and often run in threads with timeouts.
- `src/agent/tools.py` — defines `ALL_TOOLS` (search, web_fetch, web_browser, rss_reader, get_current_location, get_weather). Tools return plain text and may truncate output.
- `src/agent/model.py` — creates `_llm` from env vars (`DOUBAO_MODEL`, `DOUBAO_BASE_URL`, `DOUBAO_API_KEY`) and binds `ALL_TOOLS` to produce `model_with_tools`.
- `src/backend.py` — a small FastAPI server exposing `/run-task` which streams LangGraph events via `graph.astream(inputs)` as SSE. Useful for local debugging and frontend integration.

### State & data flow rules (required when adding/changing nodes)
- State shape: see `src/agent/states.py` — `AgentState` includes `messages`, `weather_report`, `rss_summaries`.
- Node contract:
  - Input: `state: AgentState`.
  - Output: `dict` with keys that will be merged into state (e.g. `{"weather_report": "..."}` or `{"rss_summaries": [...]}`).
  - For text output intended as the final assistant response, return `{"messages": [AIMessage(content=...)]}`.
  - Avoid mutating global state; return new values.
- Concurrency: nodes often use `concurrent.futures.ThreadPoolExecutor`. Create agent executors inside threads (executor/clients are not guaranteed thread-safe). Keep per-call timeouts (nodes use 60s or shorter).

### Patterns & gotchas discovered in code
- `aggregator_node` must produce `messages` (list of `AIMessage`) — otherwise `invoke`/frontend won't get `content`.
- Tools can return error strings rather than raise; callers expect text responses and sometimes do simple checks for `'失败'` / empty lists.
- `tools.rss_reader` performs robust heuristics for encoding and returns truncated previews — keep that behavior when refactoring.
- `model._llm.bind_tools(ALL_TOOLS)` is used to provide tool access; prefer reusing `model_with_tools` for tool-augmented calls when possible.
- The server sets `os.environ["USER_AGENT"]` and disables some SSL warnings — be careful if changing network behaviour.

### Developer workflows (exact commands)
- Quick dev server (recommended): install the LangGraph CLI and run the dev server:
  - pip (local env):
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e . "langgraph-cli[inmem]"
    langgraph dev
    ```
  - Note: `langgraph dev` hot-reloads the graph; edit `src/agent/graph.py` / `src/agent/nodes.py` and refresh.
- Tests & linters (CI mirrors commands below)
  - CI uses the `uv` wrapper (https://astral.sh/uv/) to install from `pyproject.toml`. Locally, you can either install `uv` or install packages manually:
    ```bash
    # Option A (recommended, matches CI)
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv venv
    uv pip install -r pyproject.toml
    uv pip install pytest ruff mypy
    uv run ruff check .
    uv run mypy --strict src/
    uv run pytest tests/unit_tests

    # Option B (manual)
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .
    pip install pytest ruff mypy
    ruff check .
    mypy --strict src/
    pytest tests/unit_tests
    ```

### Environment variables of interest
- `DOUBAO_MODEL`, `DOUBAO_BASE_URL`, `DOUBAO_API_KEY` — used in `src/agent/model.py` to configure the LLM.
- `LANGSMITH_API_KEY` — optional tracing via LangSmith if you enable it in `.env` (mentioned in README).

### When changing the graph
- Edit `src/agent/graph.py`:
  - `workflow.add_node("name", node_fn)` and `workflow.add_edge(from, to)` — then `graph = workflow.compile()`.
  - Keep node names in sync with any front-end expectations or tests.
- Ensure node outputs match keys in `AgentState` and that aggregator still returns `messages` when composing the final assistant output.

### Files to inspect for examples
- `src/agent/nodes.py` — concurrent node examples and how prompts are built
- `src/agent/tools.py` — examples of `@tool` wrappers and network robustness
- `src/backend.py` — SSE streaming integration and `graph.astream` usage
- `tests/unit_tests` and `tests/integration_tests` — how CI runs tests and example expectations

If any of this is incomplete or you want different emphasis (e.g., more tests, environment setup, or specific code areas to protect), tell me what to expand and I'll iterate.
