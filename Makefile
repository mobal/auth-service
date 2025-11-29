all: format lint test

bandit:
	uv run -m bandit --severity-level high --confidence-level high -r app/ -vvv

format:
	uv run ruff format .

install:
	uv sync

lint:
	uv run ruff check app/ tests/ --fix

mypy:
	uv run -m mypy app/ --explicit-package-bases

test:
	uv run -m pytest --cov-fail-under=90

unit-test:
	uv run -m pytest tests/unit

integration-test:
	uv run -m pytest tests/integration
