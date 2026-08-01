from __future__ import annotations

import secrets
from pathlib import Path

_DEFAULT_TOKEN_PATH = Path(__file__).parent.parent.parent / "data" / ".auth_token"


def get_or_create_token(path: str | Path = _DEFAULT_TOKEN_PATH) -> str:
    """Return the shared local auth token, generating one on first run.

    Any process on this machine that can read this file is trusted — this is
    not a replacement for real auth, just a floor against an arbitrary local
    process or browser tab hitting the HTTP/WS endpoints unnoticed.
    """
    token_path = Path(path)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    if token_path.exists():
        existing = token_path.read_text().strip()
        if existing:
            return existing

    token = secrets.token_urlsafe(32)
    token_path.write_text(token)
    try:
        token_path.chmod(0o600)
    except Exception:
        pass  # best-effort on platforms without POSIX permissions (e.g. Windows)
    return token
