.PHONY: install lint test test-cov run serve build up down clean

install:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check src/ tests/

lint-fix:
	.venv/bin/ruff check src/ tests/ --fix

test:
	.venv/bin/python -m pytest tests/ -q \
		--deselect tests/unit/test_cli.py::TestCLI::test_ask_with_project \
		--deselect tests/unit/test_cli.py::TestCLI::test_no_args_shows_help

test-cov:
	.venv/bin/python -m pytest tests/ \
		--deselect tests/unit/test_cli.py::TestCLI::test_ask_with_project \
		--deselect tests/unit/test_cli.py::TestCLI::test_no_args_shows_help \
		--cov=src/jarvis --cov-report=term-missing

run:
	.venv/bin/python -m jarvis

serve:
	.venv/bin/python -m jarvis serve

status:
	.venv/bin/python -m jarvis status

agents:
	.venv/bin/python -m jarvis agents

plugins:
	.venv/bin/python -m jarvis plugins scan

pipelines:
	.venv/bin/python -m jarvis pipeline list

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage
