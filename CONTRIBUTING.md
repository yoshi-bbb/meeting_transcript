# Contributing

Thank you for helping improve Meeting Mojiokoshi.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "pip==26.1.2"
python -m pip install -c requirements/constraints.txt -e ".[dev,build]"
```

## Running Checks

```bash
python -m pytest -q
python -m compileall src tests scripts
python -m bandit -r src -c pyproject.toml -ll
python -m pip_audit -r requirements/constraints.txt
```

## Pull Requests

- Keep changes focused and include tests for behavior changes.
- Do not commit recordings, generated binaries, local caches, secrets, or audit
  output.
- Update `requirements/constraints.txt` when dependency versions change.
- Follow the license terms in `LICENSE`.

Regenerate the cross-platform constraints file with:

```bash
uv pip compile pyproject.toml --all-extras --universal --upgrade \
  --python-version 3.12 --output-file requirements/constraints.txt
```

## Security

See `SECURITY.md` for vulnerability reporting guidance.
