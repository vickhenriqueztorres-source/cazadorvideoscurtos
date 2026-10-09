# LIVE HEADER FLICKER TRACE

- Renderer: WebGL
- Status: PASS
- Solution grade: B
- Classification: NONE_DETECTED
- Observed frames: 122
- Incorrect state frames: 0
- Post-render override frames: 0
- Reference/target maximum delta: 0.0 px
- Average override duration: 0.057 ms
- Maximum override duration: 1.4 ms
- Average frame interval: 16.6777 ms
- Dropped-frame estimate: 2

## Root cause

No incorrect target state reached an observed renderer draw.

## Recommended fix

Keep the renderer-local hook and re-run the trace after renderer changes.
