.PHONY: test lint typecheck format dev install clean placeholders

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/ main.py

typecheck:
	mypy src/ main.py --ignore-missing-imports

format:
	ruff format src/ tests/ main.py

dev:
	pip install -e ".[dev]"

install:
	pip install -e .

install-all:
	pip install -e ".[all]"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/

placeholders:
	python scripts/generate_placeholders.py
	python scripts/generate_word_placeholders.py
	python scripts/generate_bsl_placeholders.py
