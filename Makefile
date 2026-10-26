.PHONY: setup doctor demo test lint format serve
setup:
	bash scripts/setup.sh
doctor:
	./run.sh doctor
demo:
	./run.sh demo
test:
	.venv/bin/python -m pytest -q
lint:
	.venv/bin/ruff check src tests
	.venv/bin/ruff format --check src tests
format:
	.venv/bin/ruff format src tests
serve:
	./run.sh serve

