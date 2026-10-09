from __future__ import annotations

from enum import StrEnum


class InspectorState(StrEnum):
    BOOTING = "BOOTING"
    BROWSER_STARTING = "BROWSER_STARTING"
    BROWSER_CONNECTED = "BROWSER_CONNECTED"
    INSTRUMENTING = "INSTRUMENTING"
    READY = "READY"
    TARGET_SELECTION_ARMED = "TARGET_SELECTION_ARMED"
    TARGET_CAPTURED = "TARGET_CAPTURED"
    ANALYZING_DOM = "ANALYZING_DOM"
    ANALYZING_CANVAS = "ANALYZING_CANVAS"
    ANALYZING_WEBGL = "ANALYZING_WEBGL"
    CORRELATING = "CORRELATING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


ALLOWED: dict[InspectorState, set[InspectorState]] = {
    InspectorState.BOOTING: {InspectorState.BROWSER_STARTING, InspectorState.FAILED},
    InspectorState.BROWSER_STARTING: {InspectorState.BROWSER_CONNECTED, InspectorState.FAILED},
    InspectorState.BROWSER_CONNECTED: {InspectorState.INSTRUMENTING, InspectorState.FAILED},
    InspectorState.INSTRUMENTING: {InspectorState.READY, InspectorState.FAILED},
    InspectorState.READY: {InspectorState.TARGET_SELECTION_ARMED, InspectorState.STOPPED},
    InspectorState.TARGET_SELECTION_ARMED: {
        InspectorState.TARGET_CAPTURED,
        InspectorState.READY,
        InspectorState.FAILED,
    },
    InspectorState.TARGET_CAPTURED: {InspectorState.ANALYZING_DOM, InspectorState.FAILED},
    InspectorState.ANALYZING_DOM: {
        InspectorState.ANALYZING_CANVAS,
        InspectorState.COMPLETE,
        InspectorState.FAILED,
    },
    InspectorState.ANALYZING_CANVAS: {
        InspectorState.ANALYZING_WEBGL,
        InspectorState.CORRELATING,
        InspectorState.COMPLETE,
        InspectorState.FAILED,
    },
    InspectorState.ANALYZING_WEBGL: {InspectorState.CORRELATING, InspectorState.FAILED},
    InspectorState.CORRELATING: {InspectorState.COMPLETE, InspectorState.FAILED},
    InspectorState.COMPLETE: {InspectorState.READY, InspectorState.STOPPED},
    InspectorState.FAILED: {InspectorState.READY, InspectorState.STOPPED},
    InspectorState.STOPPED: set(),
}


class StateMachine:
    def __init__(self) -> None:
        self.current = InspectorState.BOOTING

    def transition(self, target: InspectorState) -> None:
        if target not in ALLOWED[self.current]:
            raise ValueError(f"invalid state transition: {self.current} -> {target}")
        self.current = target
