"""Shell command allowlist and dangerous-character blocklist."""
from __future__ import annotations

ALLOWED_COMMANDS = {
    "python", "py", "git", "pip", "dir", "echo", "type", "cat",
    "uptime", "whoami", "hostname",
}

DISALLOWED_CHARS = {"|", "&", ";", ">", "<", "`", "$", "\n", "\r"}
