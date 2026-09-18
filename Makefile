.PHONY: help test check

PYTHON := .venv/bin/python

help:
	@printf '%s\n' 'CivicOS commands:' '  make test   Run the test suite' '  make check  Verify Python and project imports' '  make help   Show available commands'

test:
	@test -x "$(PYTHON)" || (printf '%s\n' 'Missing .venv. Create it and install project dependencies separately.' >&2; exit 1)
	@$(PYTHON) -m pytest tests -q

check:
	@test -x "$(PYTHON)" || (printf '%s\n' 'Missing .venv. Create it and install project dependencies separately.' >&2; exit 1)
	@DATABASE_ENABLED=false DATABASE_URL='postgresql+asyncpg://user:pass@localhost:5432/civicos' MOCK_LLM=true $(PYTHON) -c 'import fastapi, httpx, pydantic, sqlalchemy; import app.main; import app.schemas.process; print("Python and project imports: OK")'
