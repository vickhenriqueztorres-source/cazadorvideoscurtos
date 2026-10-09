# FLICKER AFTER FIX

- Renderer: WebGL
- Status: PASS
- Solution grade: B
- Classification: NONE_DETECTED
- Observed frames: 120
- Incorrect state frames: 0
- Post-render override frames: 0
- Reference/target maximum delta: 0.0 px
- Average override duration: 0.0563 ms
- Maximum override duration: 12.4 ms
- Average frame interval: 17.5269 ms
- Dropped-frame estimate: 6

## Root cause

No incorrect target state reached an observed renderer draw.

## Recommended fix

Keep the renderer-local hook and re-run the trace after renderer changes.
