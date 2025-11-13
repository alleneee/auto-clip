# Task Completion Checklist
1. Ensure virtualenv/requirements up to date; export required env vars via `.env` (DashScope keys, storage config) before running services.
2. Run relevant unit/integration tests with `pytest tests/` (filter modules when possible) and confirm success.
3. For code changes touching API/Celery flows, manually hit `/health` or key endpoints (upload/task creation) against local FastAPI server to sanity-check responses.
4. Lint/format using `black .` (and re-run if files change) before handing off patches.
5. If Docker is used, rebuild/restart via `docker-compose up -d --build` and check logs (`docker-compose logs -f`) for errors.
6. Update docs/config samples when new env vars or workflows are introduced.