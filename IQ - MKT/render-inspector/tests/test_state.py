import pytest

from render_inspector.state import InspectorState, StateMachine


def test_state_machine_rejects_skipped_transition() -> None:
    state = StateMachine()
    with pytest.raises(ValueError):
        state.transition(InspectorState.READY)


def test_boot_sequence() -> None:
    state = StateMachine()
    for target in (
        InspectorState.BROWSER_STARTING,
        InspectorState.BROWSER_CONNECTED,
        InspectorState.INSTRUMENTING,
        InspectorState.READY,
    ):
        state.transition(target)
    assert state.current is InspectorState.READY
