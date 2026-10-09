from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InspectorConfig:
    root: Path
    host: str = "127.0.0.1"
    port: int = 8765
    target_url: str = "https://iqoption.com/traderoom"
    capture_level: str = "normal"
    debug: bool = False
    ring_events: int = 20_000
    batch_ms: int = 75

    @property
    def workspace(self) -> Path:
        return self.root / "workspace"

    @property
    def profile(self) -> Path:
        return self.workspace / "browser-profile"

    @property
    def sessions(self) -> Path:
        return self.workspace / "sessions"

    @property
    def panel_url(self) -> str:
        return f"http://{self.host}:{self.port}"
