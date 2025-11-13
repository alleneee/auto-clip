# Code Style & Conventions
- Language: Python 3.10+ with async FastAPI endpoints and Celery tasks; prefer type hints and Pydantic v2 `BaseModel` schemas for request/response contracts.
- Modules include short docstrings (often Chinese) and structured logging via `structlog`; middleware/order comments explain flow—mirror this style when adding features.
- Settings/config pulled from `app.config.settings` (Pydantic Settings); use constants/ENV variables rather than literals.
- Logging: use `app.utils.logger.get_logger` and structured key/value logs; avoid bare `print`.
- Formatting: project depends on `black==23.12.1`; run `black .` for formatting, keep imports organized (no explicit isort config found).
- Testing uses `pytest`/`pytest-asyncio`; name async tests with `async def` and `pytest.mark.asyncio` when needed.