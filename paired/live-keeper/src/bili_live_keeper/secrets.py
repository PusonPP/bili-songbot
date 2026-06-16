"""Helpers for keeping cookies and stream credentials out of logs."""

import re
from typing import Any, Dict


SENSITIVE_COOKIE_NAMES = {
    "SESSDATA",
    "bili_jct",
    "DedeUserID",
    "DedeUserID__ckMd5",
    "sid",
    "buvid3",
    "buvid4",
    "b_nut",
}

SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(SESSDATA=)[^;\s]+"),
    re.compile(r"(?i)(bili_jct=)[^;\s]+"),
    re.compile(r"(?i)(DedeUserID=)[^;\s]+"),
    re.compile(r"(?i)(DedeUserID__ckMd5=)[^;\s]+"),
    re.compile(r"(?i)(BILI_STREAM_KEY=).*"),
    re.compile(r"(?i)(stream[_-]?key[\"'\s:=]+)[^\"'\s&]+"),
    re.compile(r"(?i)(key=)[^&\s]+"),
    re.compile(r"(?i)(streamname=)[^&\s]+"),
    re.compile(r"(?i)(access[_-]?token[\"'\s:=]+)[^\"'\s&]+"),
]


def redact_text(value: Any) -> str:
    text = str(value)
    for pattern in SENSITIVE_PATTERNS:
        text = pattern.sub(lambda match: match.group(1) + "***redacted***", text)
    return text


def redact_cookie_name_value(name: str, value: str) -> str:
    if name in SENSITIVE_COOKIE_NAMES or name.lower() in {n.lower() for n in SENSITIVE_COOKIE_NAMES}:
        return "***redacted***"
    if not value:
        return ""
    if len(value) <= 8:
        return "***redacted***"
    return value[:4] + "***" + value[-2:]


def redact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if "cookie" in key_lower or "key" in key_lower or "token" in key_lower or "secret" in key_lower:
            redacted[key] = "***redacted***" if value else value
        else:
            redacted[key] = redact_text(value) if isinstance(value, str) else value
    return redacted


def redacted_stream_key(value: str) -> str:
    if not value:
        return ""
    return "***redacted***"


def safe_rtmp_url(value: str) -> str:
    """Return an RTMP URL suitable for logs, with query credentials removed."""
    if not value:
        return ""
    if "?" in value:
        return value.split("?", 1)[0] + "?***redacted***"
    return redact_text(value)
