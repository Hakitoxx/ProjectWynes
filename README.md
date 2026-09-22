<!-- Banner: place the project banner at docs/images/banner.png and reference it here. -->

# Project Wynes

**Version 1.2.0** — Modern Windows desktop toolkit for defensive network and system diagnostics.

Python + PySide6 + Windows · Türkçe & English UI · MIT License

Project Wynes puts everyday diagnostic work — DNS, ping, traceroute, port
checks, HTTP/TLS inspection, Nmap scans, system and process information,
file hashing — into one clean desktop application, instead of a dozen tabs
of terminals and memorized command flags.

> **Authorized use only.** Wynes is a defensive diagnostic tool for systems
> and networks you own or are explicitly permitted to inspect. It contains
> no exploitation, credential-theft or attack-automation functionality.

## Screenshots

<!-- Screenshots are added by the maintainer. Place files in docs/images/
     and link them here, e.g. ![Dashboard](docs/images/dashboard.png) -->

*Screenshots will be added to `docs/images/`.*

## Features

| Category | Tool | What it does |
|---|---|---|
| Network | DNS Lookup | Forward (A/AAAA) + reverse (PTR) resolution |
| Network | Ping | Reachability with packet/RTT statistics (locale-proof parsing) |
| Network | Traceroute | Hop-by-hop path with per-hop timing |
| Network | Port Check | Single-port TCP connectivity with clear states |
| Network | HTTP Headers | HEAD-based header inspection, redirect info, no body download |
| Network | TLS / Certificate | Handshake, cipher, certificate details, verification status |
| Network | Nmap Scan | Safe profiles via the official Nmap executable (optional) |
| System | System Information | OS, hardware, memory, runtime, uptime |
| System | Network Information | Adapters, IPv4/IPv6, MAC, gateways, DNS servers |
| System | Process List | Read-only process table (PID, name, memory, path) |
| Files | File Hash | SHA-256/SHA-512/SHA-1/MD5, streamed, fully local |

Plus: bilingual UI (Türkçe default / English, switchable live in Settings),
dark professional theme, structured results with raw output available, and
a dashboard with tool availability.

## Windows Installation

### Method 1 — PowerShell Installation

Installs the standalone executable for the current Windows user. **No
Python needed.** No admin rights needed.

1. Open **PowerShell** (Windows key → type `powershell` → Enter).
2. Run:

   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Hakitoxx/ProjectWynes/main/install.ps1" -OutFile "$env:TEMP\wynes-install.ps1"
   powershell -ExecutionPolicy Bypass -File "$env:TEMP\wynes-install.ps1"
   ```

   The installer downloads the official release package, verifies its
   SHA-256 checksum, installs to `%LOCALAPPDATA%\ProjectWynes`, and adds
   the launcher to your **user** PATH (never overwriting it).
3. **Close and reopen** the terminal (PATH changes apply to new terminals).
4. From **any** directory, run:

   ```cmd
   projectwynes
   ```

Project Wynes opens.

To remove it later:

```powershell
powershell -ExecutionPolicy Bypass -File "%LOCALAPPDATA%\ProjectWynes\uninstall.ps1"
```

### Method 2 — GitHub ZIP

Runs from the source tree. Requires **Python 3.11+**; does **not** modify
your PATH or anything outside the folder.

1. Open the repository → **Code → Download ZIP**.
2. Extract the ZIP.
3. Open the extracted `ProjectWynes-main` folder and run the setup:

   ```powershell
   powershell -ExecutionPolicy Bypass -File setup.ps1
   ```

4. Open a **CMD** window in that same folder (`File → Open command prompt`
   in Explorer, or `cmd` in the address bar) and type:

   ```cmd
   projectwynes
   ```

   (In PowerShell: `.\projectwynes.cmd`.)

Project Wynes opens.

### Security notes on installation

- Downloads come only from the official repository
  (`github.com/Hakitoxx/ProjectWynes`) over HTTPS.
- The PowerShell installer verifies the package's SHA-256 checksum before
  installing and fails safely on any mismatch.
- You are encouraged to read `install.ps1` before running it.
- Nmap is **not** bundled; install it from the official
  <https://nmap.org> site if you want the Nmap tool. Without it, Wynes
  works fully and simply marks that tool as unavailable.

## Developer setup

```powershell
git clone https://github.com/Hakitoxx/ProjectWynes.git
cd ProjectWynes
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Useful flags: `run.py --smoke-test` (headless startup check),
`run.py --lang tr|en` (force language for one run).

### Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Deterministic suite: localization key parity, validators, command
construction and output parsing, loopback-based port/HTTP/TLS checks,
hashing, system/network/process enumeration, and headless GUI smoke tests
in both languages. Nmap-dependent tests skip when Nmap is absent.

### Building the executable

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm packaging\projectwynes.spec
```

Output: `dist\projectwynes.exe` (single windowed executable).

## Project structure

```
run.py                    Entry point (--smoke-test, --lang)
projectwynes.cmd          Local launcher (Method 2)
setup.ps1                 Local setup for the ZIP method
install.ps1               PowerShell installer (Method 1)
uninstall.ps1             Removes a Method 1 installation
packaging/                PyInstaller spec + Windows version info
docs/images/              Screenshots/banner (added by maintainer)
requirements.txt          Runtime dependency: PySide6
requirements-dev.txt      Packaging toolchain
src/wynes/
  app.py                  Bootstrap + first-launch language flow
  core/                   i18n, validators, tool contracts, registry,
                          safe process execution, settings
  locale/                 tr.py / en.py string tables
  tools/                  One module per diagnostic tool
  ui/                     main_window, dashboard, tool_page, outputs,
                          settings_page, about_page, first_launch, theme
tests/                    unittest suite
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md). Please report vulnerabilities privately via
GitHub's "Report a vulnerability" feature.

## Limitations

- Windows is the primary target; the diagnostic logic is largely portable
  but the packaging and installer are Windows-specific.
- Process details for protected/system processes require running Wynes as
  administrator — shown transparently, never silently dropped.
- Nmap features require a separately installed Nmap.

## License

[MIT](LICENSE)
