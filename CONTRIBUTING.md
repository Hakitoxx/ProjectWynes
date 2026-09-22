# Contributing to Project Wynes

Thanks for your interest. Wynes is a defensive desktop diagnostics toolkit —
contributions that keep it simple, safe and maintainable are welcome.

## Development setup

```powershell
git clone https://github.com/Hakitoxx/ProjectWynes.git
cd ProjectWynes
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

Requires Python 3.11+ on Windows.

## Running the app

```powershell
.\.venv\Scripts\python.exe run.py
```

## Running tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All tests must pass before submitting a PR. Add tests for new behavior; keep
them deterministic (no external network, no admin rights).

## Building the Windows executable

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm packaging\projectwynes.spec
```

Output: `dist\projectwynes.exe`.

## Coding expectations

- Keep the architecture: tools in `src/wynes/tools/`, UI in `src/wynes/ui/`,
  contracts in `src/wynes/core/`.
- All user-facing text goes through `tr()` with keys in `src/wynes/locale/`
  (`en.py` + `tr.py` — keep both in sync; a test enforces key parity).
- External processes: argument lists only, never `shell=True`.
- No new dependencies without a clear justification in the PR.
- English identifiers (classes, functions, modules); Turkish comments allowed.

## Issues and pull requests

- Use the issue templates (bug report / feature request).
- One focused change per PR; describe what, why, and how it was tested.
- UI changes: attach screenshots.

## Security-sensitive changes

Changes to process execution, input validation, installers, or anything
touching files outside the project directory get extra scrutiny. Do not
include credentials, tokens or private data anywhere.
