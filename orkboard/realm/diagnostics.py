"""Where Orkboard runs, for whoever looks into an error (the owner's notes of 19 October): its version, the Python and
the machine, each AI tool as this process finds it (the path it runs, its version, whether it looks signed in) and
which of the environment's sign-in settings are set. Saved as `about.json` beside the day's logs (gui/logs_save.py).

The values of the environment are never written, only whether each is set, except for the few that hold no secret
(paths, the shell): a key's presence is what tells why a tool that is signed in in a terminal is not in Orkboard.

    about(machine)                         # {"orkboard", "python", "platform", "launched", "tools": [...], "env": {...}}
                                           # a tool's row: path, version, signed in; Claude's its `claude auth status`

No face, no model.
"""
from __future__ import annotations

import os
import platform
import sys
from typing import Any, Callable

from orkboard import __version__

# What decides which account an AI tool runs on: shown as set or not, never their values.
SIGN_IN_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL",
               "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
# What holds no secret and says where a tool looks: shown as they are.
SHOWN_ENV = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "HOME", "SHELL", "PATH", "ORKBOARD_FROM")


def env_of(env: dict | None = None) -> dict[str, str]:
    """The environment's sign-in settings as "set" (never their values), and the few that hold no secret as they are."""
    env = dict(os.environ) if env is None else env
    out = {name: "set" for name in SIGN_IN_ENV if env.get(name)}
    out.update({name: str(env[name]) for name in SHOWN_ENV if env.get(name)})
    return out


def about(machine: Any = None, detect: Callable[[], list] | None = None, env: dict | None = None,
          auth: Callable[[str], dict] | None = None) -> dict:
    """Orkboard, its Python and machine, how it was started, each AI tool as this process finds it, and the
    environment as `env_of` says it. `detect`: tools.detect (it asks each tool found its version); `auth`:
    tools.claude_auth, Claude Code's own word on its sign-in here (a terminal's may differ: another config folder)."""
    from orkboard import tools
    env = dict(os.environ) if env is None else env
    auth = auth or (lambda path: tools.claude_auth(path, env=env))
    chosen = getattr(machine, "tools", None) or {}
    found = []
    for s in (detect or tools.detect)():
        choice = chosen.get(s.tool.id)
        found.append({"id": s.tool.id, "found": s.found, "path": s.path, "version": s.version,
                      "signed_in": s.logged_in, "billing_seen": s.billing,
                      "turned_on": bool(getattr(choice, "enabled", False)), "billing": getattr(choice, "billing", ""),
                      **({"auth_status": auth(s.path)} if s.tool.id == "claude" and s.found else {})})
    return {"orkboard": __version__, "python": sys.version.split()[0], "executable": sys.executable,
            "platform": platform.platform(), "launched": env.get("ORKBOARD_FROM") or "terminal",
            "cwd": os.getcwd(), "tools": found, "env": env_of(env)}
