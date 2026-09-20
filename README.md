# Project Wynes

**Version 1.2.0**

A minimalist desktop toolkit for defensive network and system diagnostics.
Wynes bundles focused diagnostic tools behind one clean, bilingual
(Türkçe / English) desktop interface — a "Swiss Army knife" for authorized
troubleshooting, learning and administration.

> **Scope:** Wynes is a defensive diagnostic tool. Use it only on systems
> and networks you own or are explicitly authorized to inspect. It contains
> no exploit, credential-theft, persistence or attack-automation
> functionality.

## Features

| Category | Tool | What it does |
|---|---|---|
| Network | **DNS Lookup** | Forward (A/AAAA) and reverse (PTR) resolution via the system resolver |
| Network | **Ping** | Reachability, packet and RTT statistics via the system ping (locale-proof parsing) |
| Network | **Traceroute** | Hop-by-hop route via the system tracert/traceroute with per-hop timing |
| Network | **Port Check** | Single TCP connect test with state explanation (open/closed/filtered/DNS) |
| Network | **HTTP Headers** | HEAD-based header inspection; redirect reporting; no content download |
| Network | **TLS / Certificate** | Handshake, negotiated protocol/cipher, certificate chain details, verification status |
| Network | **Nmap Scan** | Safe profiles via the official Nmap CLI (see below) |
| System | **System Information** | OS, hardware, memory, runtime, uptime |
| System | **Network Information** | Adapters, IPv4/IPv6, MAC, link state, gateways, DNS servers |
| System | **Process List** | Read-only process table (PID, name, memory, path), filterable |
| Files | **File Hash** | SHA-256/SHA-512/SHA-1/MD5 with stream processing (local only) |

Plus: **Dashboard** with tool availability overview and quick access,
**Settings** (language, Nmap path), **About**, localized validation and
error messages, raw-output sections for technical detail.

## Localization

The entire UI is bilingual: **Türkçe** (default) and **English**.
On first launch a language dialog is shown; the choice is persisted and
can be changed anytime in *Settings*. All UI text lives centrally in
`src/wynes/locale/` (`tr.py`, `en.py`) — no language conditionals are
scattered through the code.

## Requirements

- Windows 10/11 (primary target; the code itself is largely cross-platform)
- Python 3.11+ (developed on 3.14)
- [Nmap](https://nmap.org/) — **optional**, only needed for the Nmap tool

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

Useful flags: `--smoke-test` (headless startup check), `--lang tr|en`
(force language for one run).

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite covers localization key parity, validators, command construction
and output parsing (ping/traceroute/Nmap), loopback-based port/HTTP/TLS
checks, hashing, system/network/process enumeration and headless GUI
smoke tests in both languages. Nmap-dependent tests skip automatically
when Nmap is not installed.

## Nmap integration

Wynes uses the **official Nmap executable** (never bundled source):

- Detection order: custom path from Settings → `PATH` → default install
  locations (`C:\Program Files (x86)\Nmap`, `C:\Program Files\Nmap`)
- Version detection via `nmap --version`
- Execution with argument lists (no shell, no string concatenation),
  timeouts and robust console-output decoding
- Deliberately limited profiles: host discovery (`-sn`), quick TCP scan
  (`-sT`), service detection (`-sV`); targets limited to single hosts or
  CIDR ranges of /24 at most — **no** exploit scripts, no OS
  fingerprinting, no mass scanning
- If Nmap is missing, the tool page explains how to install it instead of
  failing

## Project structure

```
run.py                  Entry point (--smoke-test, --lang)
requirements.txt        Single dependency: PySide6
src/wynes/
  app.py                Bootstrap, first-launch language flow
  core/
    i18n.py             Central localization runtime (tr(), listeners)
    validators.py       Shared input validation (host/port/URL/file)
    tool_base.py        Tool contract, ToolResult, InputField, TableData
    tool_manager.py     Tool registry + availability cache
    process.py          Safe external-process execution + console decoding
    settings.py         QSettings persistence
  locale/               tr.py / en.py string tables
  tools/                One module per diagnostic tool
  ui/                   main_window, dashboard, tool_page, outputs,
                        settings_page, about_page, first_launch, theme
tests/                  unittest suite (deterministic, loopback-based)
```

## Security & privacy notes

- External processes run without a shell, with argument lists and timeouts.
- Console output is decoded code-page-safely; no raw tracebacks reach the UI.
- User input is validated before any process or network operation
  (including command-line-injection guards).
- File hashing is fully local; process/system/network info never leaves
  the machine; external traffic happens only when *you* run an HTTP/TLS/
  Nmap diagnostic.
- No secrets, tokens or credentials are stored or committed (`.gitignore`
  covers `.env` files and key material).

## Limitations

- Nmap features require a separately installed Nmap.
- Process details for protected/system processes require running Wynes as
  administrator (reported transparently, not hidden).
- Windows Northern-Europe-style console quirks are handled, but ping and
  tracert parsing focuses on the protocol-stable parts of their output.
