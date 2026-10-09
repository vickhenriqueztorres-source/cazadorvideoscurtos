from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image

from render_inspector.models import ArtifactInfo


class ArtifactStore:
    def __init__(self, session_dir: Path) -> None:
        self.root = session_dir / "analyses"
        self.root.mkdir(parents=True, exist_ok=True)

    def analysis_dir(self, analysis_id: str) -> Path:
        path = self.root / analysis_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_bytes(
        self, analysis_id: str, name: str, data: bytes, media_type: str | None = None
    ) -> ArtifactInfo:
        path = self.analysis_dir(analysis_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return ArtifactInfo(
            path=str(path.resolve()),
            sha256=hashlib.sha256(data).hexdigest(),
            size=len(data),
            media_type=media_type,
        )

    def write_json(self, analysis_id: str, name: str, data: dict[str, Any]) -> ArtifactInfo:
        raw = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
        return self.write_bytes(analysis_id, name, raw, "application/json")

    def save_screenshot(
        self, analysis_id: str, screenshot_b64: str, crop: tuple[int, int, int, int]
    ) -> list[ArtifactInfo]:
        raw = base64.b64decode(screenshot_b64)
        full = self.write_bytes(analysis_id, "target_full.png", raw, "image/png")
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        x, y, width, height = crop
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(image.width, x0 + max(1, width)), min(image.height, y0 + max(1, height))
        out = io.BytesIO()
        image.crop((x0, y0, x1, y1)).save(out, "PNG")
        cropped = self.write_bytes(analysis_id, "target_crop.png", out.getvalue(), "image/png")
        return [full, cropped]
