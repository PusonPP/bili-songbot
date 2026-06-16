"""Cookie loading and conversion for requests and Playwright."""

import json
import logging
import time
from dataclasses import dataclass
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

from .secrets import SENSITIVE_COOKIE_NAMES

LOGGER = logging.getLogger(__name__)

DEFAULT_COOKIE_DOMAIN = ".bilibili.com"


class CookieError(RuntimeError):
    pass


@dataclass
class CookieBundle:
    path: Path
    mtime: float
    cookies: List[Dict[str, Any]]

    def requests_dict(self) -> Dict[str, str]:
        return {cookie["name"]: cookie["value"] for cookie in self.cookies if cookie.get("name")}

    def playwright_cookies(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        now = int(time.time())
        for cookie in self.cookies:
            name = str(cookie.get("name", "")).strip()
            value = str(cookie.get("value", ""))
            if not name:
                continue
            expires = _int_or_none(cookie.get("expires"))
            if expires and expires > 0 and expires < now:
                continue
            item: Dict[str, Any] = {
                "name": name,
                "value": value,
                "domain": _domain_from_cookie(cookie),
                "path": str(cookie.get("path") or "/"),
                "secure": bool(cookie.get("secure", True)),
                "httpOnly": bool(cookie.get("httpOnly", cookie.get("http_only", False))),
            }
            if expires and expires > 0:
                item["expires"] = expires
            same_site = cookie.get("sameSite") or cookie.get("same_site")
            if same_site in {"Strict", "Lax", "None"}:
                item["sameSite"] = same_site
            result.append(item)
        return result


class CookieProvider:
    def __init__(self, path: Optional[Path]):
        self.path = path.expanduser() if path else None
        self._bundle: Optional[CookieBundle] = None

    def load(self, force: bool = False) -> CookieBundle:
        if not self.path:
            raise CookieError("BILIUP_COOKIE_FILE 未配置。")
        if not self.path.exists():
            raise CookieError("cookies 文件不存在: %s" % self.path)

        stat = self.path.stat()
        if not force and self._bundle and self._bundle.mtime == stat.st_mtime:
            return self._bundle

        text = self.path.read_text(encoding="utf-8", errors="replace")
        cookies = normalize_cookies(parse_cookie_text(text))
        if not cookies:
            raise CookieError("未能从 cookies 文件解析出任何 cookie: %s" % self.path)
        self._bundle = CookieBundle(self.path, stat.st_mtime, cookies)
        names = {cookie.get("name") for cookie in cookies}
        missing_core = {"SESSDATA", "bili_jct"} - names
        LOGGER.info(
            "Loaded cookies path=%s mtime=%s count=%s missing_core=%s",
            self.path,
            int(stat.st_mtime),
            len(cookies),
            sorted(missing_core),
        )
        return self._bundle


def parse_cookie_text(text: str) -> List[Dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        data = json.loads(stripped)
        return parse_cookie_json(data)
    except json.JSONDecodeError:
        pass
    if "\t" in stripped and any(line.startswith(".") or "TRUE" in line for line in stripped.splitlines()):
        return parse_netscape_cookies(stripped)
    return parse_cookie_header(stripped)


def parse_cookie_json(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in (_cookie_from_mapping(x) for x in data) if item]
    if isinstance(data, dict):
        for key in ("cookies", "cookie", "cookie_info", "data"):
            if key in data:
                value = data[key]
                if isinstance(value, dict) and "cookies" in value:
                    value = value["cookies"]
                if isinstance(value, str):
                    parsed = parse_cookie_header(value)
                    if parsed:
                        return parsed
                parsed = parse_cookie_json(value)
                if parsed:
                    return parsed
        if "cookie_string" in data and isinstance(data["cookie_string"], str):
            return parse_cookie_header(data["cookie_string"])
        if all(not isinstance(value, (dict, list)) for value in data.values()):
            return [
                {
                    "name": str(name),
                    "value": "" if value is None else str(value),
                    "domain": DEFAULT_COOKIE_DOMAIN,
                    "path": "/",
                    "secure": True,
                }
                for name, value in data.items()
                if _looks_like_cookie_name(str(name))
            ]
        nested: List[Dict[str, Any]] = []
        for value in data.values():
            if isinstance(value, (dict, list)):
                nested.extend(parse_cookie_json(value))
        return nested
    return []


def parse_netscape_cookies(text: str) -> List[Dict[str, Any]]:
    cookies: List[Dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts = line.split()
        if len(parts) < 7:
            continue
        domain, _include_subdomains, path, secure, expires, name, value = parts[:7]
        cookies.append(
            {
                "domain": domain,
                "path": path or "/",
                "secure": secure.upper() == "TRUE",
                "expires": _int_or_none(expires),
                "name": name,
                "value": value,
            }
        )
    return cookies


def parse_cookie_header(text: str) -> List[Dict[str, Any]]:
    simple = SimpleCookie()
    try:
        simple.load(text)
    except Exception:
        return []
    cookies = []
    for name, morsel in simple.items():
        if not _looks_like_cookie_name(name):
            continue
        cookies.append(
            {
                "name": name,
                "value": morsel.value,
                "domain": DEFAULT_COOKIE_DOMAIN,
                "path": "/",
                "secure": True,
            }
        )
    return cookies


def normalize_cookies(cookies: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for cookie in cookies:
        item = _cookie_from_mapping(cookie)
        if not item:
            continue
        key = (item["name"], item.get("domain") or DEFAULT_COOKIE_DOMAIN, item.get("path") or "/")
        normalized[key] = item
    return list(normalized.values())


def _cookie_from_mapping(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    name = value.get("name") or value.get("key")
    cookie_value = value.get("value")
    if name is None or cookie_value is None:
        return None
    item = dict(value)
    item["name"] = str(name)
    item["value"] = str(cookie_value)
    item["domain"] = _domain_from_cookie(item)
    item["path"] = str(item.get("path") or "/")
    if "expires" not in item:
        item["expires"] = item.get("expirationDate") or item.get("expire") or item.get("expiry")
    if "httpOnly" not in item and "http_only" in item:
        item["httpOnly"] = bool(item["http_only"])
    return item


def _domain_from_cookie(cookie: Dict[str, Any]) -> str:
    domain = cookie.get("domain") or cookie.get("host") or cookie.get("url")
    if not domain:
        return DEFAULT_COOKIE_DOMAIN
    domain_text = str(domain)
    if domain_text.startswith("http://") or domain_text.startswith("https://"):
        parsed = urlparse(domain_text)
        return parsed.hostname or DEFAULT_COOKIE_DOMAIN
    if domain_text == "bilibili.com":
        return ".bilibili.com"
    return domain_text


def _int_or_none(value: Any) -> Optional[int]:
    if value in (None, "", "None"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _looks_like_cookie_name(name: str) -> bool:
    if name in SENSITIVE_COOKIE_NAMES:
        return True
    return bool(name) and "=" not in name and ";" not in name and len(name) <= 80
