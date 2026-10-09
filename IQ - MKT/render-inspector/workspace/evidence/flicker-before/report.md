# FLICKER BEFORE FIX

- Renderer: WebGL
- Status: FAIL
- Solution grade: E
- Classification: POST_RENDER_OVERRIDE, REFERENCE_TARGET_CLOCK_DESYNC, ONE_FRAME_LATE_TRACKING
- Observed frames: 120
- Incorrect state frames: 120
- Post-render override frames: 120
- Reference/target maximum delta: 2.4984 px
- Average override duration: 0.015 ms
- Maximum override duration: 0.2 ms
- Average frame interval: 17.384 ms
- Dropped-frame estimate: 3

## Root cause

The visual override begins after a renderer draw in the same observable frame.

## Recommended fix

Move the remap into the state update or immediately before the native draw.
