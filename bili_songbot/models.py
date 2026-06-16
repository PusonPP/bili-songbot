from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TransitionPolicy:
    enabled: bool = True
    mode: str = "alpha_overlay"
    transition_asset: str = "media/transition/transition_720p30_argb.mov"
    overlap_seconds: float | None = None


@dataclass(slots=True)
class Song:
    song_id: str
    display_name: str
    file_path: str
    aliases: list[str]
    duration: float = 0.0
    weight: float = 1.0
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    normalized_file_path: str = ""
    preprocessed_file_path: str = ""
    transition_policy: TransitionPolicy = field(default_factory=TransitionPolicy)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Song":
        tp = data.get("transition_policy") or {}
        return cls(
            song_id=str(data["song_id"]),
            display_name=str(data["display_name"]),
            file_path=str(data.get("file_path", "")),
            aliases=[str(x) for x in data.get("aliases", [])],
            duration=float(data.get("duration") or 0.0),
            weight=float(data.get("weight") or 1.0),
            enabled=bool(data.get("enabled", True)),
            tags=[str(x) for x in data.get("tags", [])],
            notes=str(data.get("notes", "")),
            normalized_file_path=str(data.get("normalized_file_path", "")),
            preprocessed_file_path=str(data.get("preprocessed_file_path", "")),
            transition_policy=TransitionPolicy(
                enabled=bool(tp.get("enabled", True)),
                mode=str(tp.get("mode", "alpha_overlay")),
                transition_asset=str(tp.get("transition_asset", "media/transition/transition_720p30_argb.mov")),
                overlap_seconds=(float(tp["overlap_seconds"]) if tp.get("overlap_seconds") is not None else None),
            ),
        )

    @property
    def runtime_path(self) -> str:
        return self.preprocessed_file_path or self.normalized_file_path or self.file_path


@dataclass(slots=True)
class QueueItem:
    song_id: str
    uid: str
    uname: str
    requested_at: float


@dataclass(slots=True)
class RequestResult:
    accepted: bool
    code: str
    message: str
    song_id: str | None = None
    display_name: str | None = None


@dataclass(slots=True)
class RuntimeStatus:
    ok: bool = True
    current_song_id: str | None = None
    current_display_name: str | None = None
    current_started_at: float | None = None
    queue_size: int = 0
    danmaku_connected: bool = False
    pusher_running: bool = False
    last_error: str = ""
    last_event_at: float | None = None
