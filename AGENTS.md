# Repository Guidelines

## Project Structure & Module Organization
`app/` hosts the FastAPI service: `api/` exposes routes, `services/` orchestrates video + LLM pipelines, `workers/` contains Celery tasks, and `utils/` supplies media helpers. Shared prompts, adapters, and tools sit under their named folders to keep agents modular. Support assets live in `docs/` and `examples/`, while automation scripts reside in `scripts/`. Persistent artifacts belong in `storage/`; short-lived clips and logs stay inside `tmp/` and `logs/`. Tests mirror the runtime layout inside `tests/` for quick navigation.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` — install Python 3.10 dependencies.
- `docker-compose up -d` — boot API, Redis, and worker containers for parity runs.
- `python -m app.main` — start FastAPI locally; pair with `celery -A app.workers.celery_app worker -l info` for background jobs.
- `pytest` or `pytest tests/test_oss_utils.py -k upload` — execute the full or targeted suite.
- `black app tests` — format touched files prior to review.

## Coding Style & Naming Conventions
Follow Black’s 4-space indentation, include type hints, and document nontrivial functions. Use `snake_case` for modules/functions, `PascalCase` for classes, and upper-snake for config constants. Favor dependency-injected services from `app.services` instead of ad-hoc globals, and keep new agents or adapters named `<feature>_agent.py` or `<provider>_adapter.py` for grepable discovery.

## Testing Guidelines
Pytest with `pytest-asyncio` is the default harness. Create files named `test_<module>.py`, keep test names descriptive, and clean any sample media written to `tmp/`. Cover success and failure flows (e.g., `get_video_info` handles corrupt clips, OSS uploads warn on missing keys). When adding CLI helpers, include smoke tests or doc snippets showing the command invocation.

## Commit & Pull Request Guidelines
Commits follow a Conventional Commit style such as `feat: add hybrid storage switch` or `docs(readme): clarify pipeline`. Keep subjects under 72 characters and explain intent when the diff is complex. Pull requests should link issues, list validation commands/logs, note config or schema changes, and attach screenshots or sample task payloads when media output changes. Tag the agent responsible for the touched module and wait for ✅ CI before merging.

## Security & Configuration Tips
Copy `.env.example` to `.env`, fill secrets (`DASHSCOPE_API_KEY`, OSS keys), and never commit the result. Large videos stay in OSS or `storage/`; prune `tmp/` before opening a PR. Document any Dockerfile or Compose changes—including exposed ports and new environment variables—in `docs/` so teammates can reproduce the pipeline safely.
