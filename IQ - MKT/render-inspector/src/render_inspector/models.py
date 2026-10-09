from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    PROBABLE = "PROBABLE"
    INCONCLUSIVE = "INCONCLUSIVE"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class BrowserTarget(BaseModel):
    target_id: str
    type: str
    title: str = ""
    url: str = ""
    attached: bool = False
    session_id: str | None = None
    opener_id: str | None = None


class FrameInfo(BaseModel):
    frame_id: str
    target_id: str
    parent_frame_id: str | None = None
    url: str = ""
    name: str = ""


class ExecutionContextInfo(BaseModel):
    context_id: int
    target_id: str
    frame_id: str | None = None
    origin: str = ""
    name: str = ""


class WorkerInfo(BaseModel):
    target_id: str
    type: str
    url: str
    session_id: str | None = None


class CanvasInfo(BaseModel):
    canvas_id: str
    target_id: str | None = None
    frame_id: str | None = None
    context_type: str
    width: int
    height: int
    css_width: float | None = None
    css_height: float | None = None
    rect: dict[str, float] | None = None
    created_at: float


class CanvasTextEvent(BaseModel):
    canvas_id: str
    api: str
    text: str
    x: float
    y: float
    font: str
    fill_style: str
    stroke_style: str
    global_alpha: float
    text_align: str
    text_baseline: str
    direction: str
    transform: dict[str, float]
    bbox: list[dict[str, float]]
    timestamp: float


class CanvasImageEvent(BaseModel):
    canvas_id: str
    args: list[Any]
    timestamp: float


class WebGLShaderInfo(BaseModel):
    shader_id: str
    shader_type: int | None = None
    source: str = ""
    compiled: bool | None = None


class WebGLProgramInfo(BaseModel):
    program_id: str
    shaders: list[str] = Field(default_factory=list)
    linked: bool | None = None


class WebGLTextureInfo(BaseModel):
    texture_id: str
    width: int | None = None
    height: int | None = None
    source_kind: str | None = None
    active_unit: int | None = None


class WebGLBufferInfo(BaseModel):
    buffer_id: str
    target: int | None = None
    byte_length: int | None = None


class WebGLUniformInfo(BaseModel):
    uniform_id: str
    program_id: str | None = None
    name: str | None = None
    api: str | None = None
    value: list[Any] = Field(default_factory=list)


class WebGLDrawCall(BaseModel):
    draw_id: str
    canvas_id: str
    api: str
    program_id: str | None = None
    textures: list[str] = Field(default_factory=list)
    uniforms: dict[str, Any] = Field(default_factory=dict)
    viewport: list[int] = Field(default_factory=list)
    scissor: list[int] = Field(default_factory=list)
    timestamp: float


class TargetSelection(BaseModel):
    target_id: str
    frame_id: str | None = None
    execution_context_id: int | None = None
    client_x: float
    client_y: float
    page_x: float
    page_y: float
    screen_x: float
    screen_y: float
    device_pixel_ratio: float
    viewport_width: float
    viewport_height: float
    scroll_x: float
    scroll_y: float
    frame_url: str
    timestamp: float
    elements: list[dict[str, Any]] = Field(default_factory=list)


class AnalysisCandidate(BaseModel):
    kind: str
    status: EvidenceStatus
    score: float | None = None
    evidence: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class ArtifactInfo(BaseModel):
    path: str
    sha256: str
    size: int
    media_type: str | None = None


class AnalysisResult(BaseModel):
    analysis_id: str
    status: EvidenceStatus
    renderer: str
    selection: TargetSelection
    candidates: list[AnalysisCandidate] = Field(default_factory=list)
    artifacts: list[ArtifactInfo] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class SessionInfo(BaseModel):
    session_id: str
    status: str
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    browser_pid: int | None = None
    browser_version: str | None = None
    cdp_version: str | None = None
