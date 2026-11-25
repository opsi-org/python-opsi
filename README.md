# python-opsi

`opsi` is a Python package with shared libraries for OPSI tooling and services.

It includes helpers for archives, compression, cryptography, files, logging, networking, OPSI packages and services, processes, serialization, system integration, testing, time handling, and utility functions.

## Installation

Python 3.13 or newer is required.

```sh
uv sync
```

Use the package from Python via the `opsi` namespace, for example:

```python
from opsi.process import run_command
```

Password hashing and verification via `opsi.crypt.hash` support SHA512-crypt and
MD5-crypt on both Linux and Windows. Their Unix shadow hash formats, SHA512 rounds,
and fixed salts when using `generate_salt=False` are unchanged.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for setup, checks, tests, and platform notes.

## License

This project is licensed under AGPL-3.0-only.
