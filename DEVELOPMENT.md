# Development

This package requires Python 3.13 or newer and uses `uv` for dependency management.

## Setup

```sh
uv sync
```

The project is installed as a package from the workspace, so imports should use `opsi.*` directly.

## Checks

Run the checks that match your change before opening a pull request:

```sh
uv run ruff check .
uv run ruff format .
uv run ty check
uv run pytest
```

For a focused test run, pass the test path or marker to `pytest`, for example:

```sh
uv run pytest tests/network/test_network.py -k test_ip_address_in_network
```

## Platform Notes

Some tests are platform-specific and use pytest markers such as `linux`, `windows`, `macos`, `posix`, `admin_permissions`, and `not_in_docker`. Use markers instead of adding ad-hoc platform checks in tests.

For tests or debugging that require Windows SYSTEM rights, start PowerShell with PsExec:

```sh
PsExec.exe -i -s powershell.exe
```
