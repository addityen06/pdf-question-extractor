# Contributing

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally

```bash
git clone https://github.com/<your-username>/pdf-question-extractor.git
cd pdf-question-extractor
```

3. Create a virtual environment and install with development dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test,dev]"
```

## Project Structure

Source code lives under `src/pdfextract/`. The package is installed in editable mode so changes take effect immediately without reinstalling.

## Running Tests

```bash
pytest tests/unit/
```

To also run integration tests (requires a fixture PDF at `tests/fixtures/sample_paper.pdf`):

```bash
pytest -m integration
```

To run all tests with coverage:

```bash
pytest --cov=src/pdfextract --cov-report=term-missing
```

## Code Style

This project uses `ruff` for linting. Run before committing:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Making Changes

- Keep each stage module focused on its responsibility
- New detection heuristics go in the appropriate `content/` or `layout/` module
- New configuration parameters go in `core/config.py` with a matching entry in `config/default.yaml`
- Every new module should have corresponding unit tests in `tests/unit/`
- Do not add external AI or cloud API dependencies — this pipeline is intentionally local-first

## Submitting a Pull Request

1. Create a branch from `main`
2. Make your changes with tests
3. Ensure all tests pass
4. Open a pull request against `main` with a clear description of what changed and why
