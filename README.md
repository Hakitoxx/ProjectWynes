# Project Wynes

A minimalist desktop toolkit for defensive network and system diagnostics.
Wynes bundles small, focused diagnostic tools behind one clean dark
interface — a "Swiss Army knife" for authorized troubleshooting and
defensive security work.

> **Scope:** Wynes is built for legitimate, defensive, educational and
> authorized diagnostic use only. It is not an attack tool and contains no
> exploitation, credential-theft or persistence functionality.

## Status

Early development. Working today:

- **Dashboard** — tool availability and local system information at a glance
- **DNS Lookup** — forward (A/AAAA) and reverse (PTR) resolution via the
  system resolver

Planned next (visible as "Planned" in the app): Ping, Traceroute, Port
Check, HTTP Headers, TLS/Certificate Info, File Hash, Process List, and
Nmap integration.

## Requirements

- Windows 10/11 (primary target; the code itself is cross-platform)
- Python 3.11+ (developed on 3.14)
- [Nmap](https://nmap.org/) — optional, only needed for the future Nmap tool

## Installation

```powershell
git clone https://github.com/Hakitoxx/ProjectWynes.git
cd ProjectWynes
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running

```powershell
.\.venv\Scripts\python.exe run.py
```

In a terminal with the venv activated, `python run.py` is enough.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Building

Packaging (single Windows executable via PyInstaller) is part of a later
milestone and not yet available.

## Nmap integration (planned)

Wynes will use the official Nmap command-line executable if present:

- detection via `PATH`, with a user-configurable override in Settings
- version detection via `nmap --version`
- execution with argument lists (never shell strings), timeouts and full
  output capture
- if Nmap is missing, the tool reports itself unavailable instead of
  failing silently

No Nmap source code is or will be vendored into this repository.

## Project structure

```
run.py                 Entry point
requirements.txt       Single dependency: PySide6
src/wynes/
  app.py               QApplication bootstrap
  core/
    tool_base.py       Tool contract, ToolResult, InputField
    tool_manager.py    Tool registry and availability cache
    process.py         Safe external-process execution helpers
    settings.py        QSettings-based persistence
  tools/               One module per diagnostic tool
  ui/
    main_window.py     Sidebar navigation + page stack
    dashboard.py       Start page
    tool_page.py       Generic per-tool page (form, worker, results)
    outputs.py         Reusable ToolResult renderer
    widgets.py         Shared UI building blocks
    theme.py           Black/white/gray QSS theme
tests/                 unittest suite for the core layer
```

## Security notes

- External processes are executed without a shell, with argument lists and
  timeouts.
- User input is validated before any process or network operation.
- No secrets, tokens or credentials are stored by the application or in
  this repository (`.gitignore` covers `.env` files and key material).
