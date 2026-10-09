# FLICKER DIAGNOSTIC

## CURRENT PIPELINE

The owned browser is instrumented through CDP before application scripts execute. The live header is
rendered by WebGL and uses interleaved vertex buffers with `a_position`, `a_color`, and atlas UV data.
The active pipeline is:

```text
application state / streamed vertex data
→ bufferData or bufferSubData interception
→ target-specific color, alpha, and position remap
→ final pre-draw validation
→ native drawElements
→ browser presentation
```

An initial `bufferData` may place original bytes in GPU storage, but no presentation occurs at upload.
Before the first native `drawElements`, the editor identifies the target vertices and uploads the
corrected byte range. Later `bufferSubData` writes are remapped before they reach the native WebGL
method. Python/CDP receives evidence asynchronously and is not part of the per-frame correction.

The application is hybrid only for optional account-menu/toast fallback. The header balance,
geometry, deposit border, and icon suppression do not use that visual overlay. The overlay root may
exist, but its visual children are hidden while the header vertex mode is active.

## TIMING

Live trace, 1920×945 viewport:

- 122 observed frames
- 0 frames with incorrect target state at draw
- 0 post-render override frames
- 0 px maximum reference/target motion delta
- 0.0570 ms average override duration
- 1.4 ms maximum override duration
- 0.0300 ms average observed draw duration
- 16.6777 ms average frame interval
- 0 dropped trace events

The two intervals above 25 ms in the live sample are an observational dropped-frame estimate; the
trace does not attribute them to the override. The override average is about 0.34% of a 16.67 ms
60 FPS budget.

## RENDERER TYPE

The selected live target is WebGL. Its motion source is the renderer's `a_position` vertex stream,
not DOM geometry, OCR, screenshot tracking, or a CSS transform. Its color and icon state are carried
by the interleaved `a_color` bytes and atlas-backed vertices.

Canvas2D and WebGL uniform pre-draw remappers are also implemented and covered by isolated fixtures.
Workers and OffscreenCanvas remain instrumented by the existing early worker bootstrap, but neither
is the modification point for this live header target.

## MODIFICATION POINT

The live correction has two renderer-local entry points:

1. Known streamed buffers are rewritten inside `bufferSubData` before the native upload.
2. Newly allocated or rotated buffers are discovered and patched inside the `drawElements` wrapper
   before the native draw is called.

The deposit icon is suppressed by setting the target vertex alpha to zero. The rounded button's
outer and inner left edges are moved as one component. Account motion is derived from the same
incoming position bytes in the same frame, so it does not read pixels from a previously presented
frame.

## WHY FLICKER CAN OCCUR

The controlled old pipeline reproduced the failure:

```text
draw orange target
→ native draw completes
→ override runs
→ current framebuffer remains orange
→ next frame repeats
```

Results for 120 controlled frames:

- 120 incorrect/orange frames
- 120 post-render override frames
- non-zero reference/target motion delta
- classifications: `POST_RENDER_OVERRIDE`, `ONE_FRAME_LATE_TRACKING`, and
  `REFERENCE_TARGET_CLOCK_DESYNC`
- solution grade: E

The optional menu/toast fallback still uses `readPixels`, a microtask, DOM canvases, MutationObserver,
and timers. It is explicitly a Grade D fallback and can have independent compositor timing when it
is visible. It is not used for the main header correction measured here.

## ROOT CAUSE

The flicker architecture is caused by modifying a previously drawn or presented result rather than
the state consumed by the renderer. Pixel capture plus overlay also introduces a separate clock and
can make target motion one frame late.

For the header, that architecture has been removed. The remap now runs before the native draw in the
same WebGL context. The live trace found no post-render header override.

## RECOMMENDED FIX

Keep the header on the current Grade B renderer-local path:

- preserve `PRE_RENDER_REMAP`, `REFERENCE_SYNC`, `ICON_SUPPRESSION`, and `COLOR_REMAP`;
- use `FLICKER DIAGNOSE` after changes to the platform renderer;
- identify targets by program/buffer/attribute region rather than applying global uniform changes;
- keep Python/CDP limited to discovery, configuration, evidence, and reports;
- migrate the optional menu/toast fallback to target-specific vertex/draw interception if zero
  compositor-delay risk is required for those temporary surfaces too.

## BEFORE / AFTER EVIDENCE

Controlled after-fix run:

- 120/120 Canvas2D frames green, 0 orange
- 120/120 WebGL uniform frames green, 0 orange
- 0 incorrect-state frames
- 0 post-render override frames
- 0 px motion delta
- status: `PASS`

Live external page run:

- status: `NO_FLICKER_OBSERVED`
- 0/122 incorrect-state frames
- 0 post-render override frames
- 0 px motion delta

`ZERO_FLICKER_CONFIRMED` applies only to the controlled fixtures. The external site result is reported
as `NO_FLICKER_OBSERVED`, as required by the evidence policy.

## FEATURE FLAGS AND REVERSAL

The active rule exposes `FLICKER_TRACE`, `PRE_RENDER_REMAP`, `REFERENCE_SYNC`, `ICON_SUPPRESSION`,
`COLOR_REMAP`, and `OVERLAY_FALLBACK`. `globalThis.__riVisualControl.disable()` restores original
buffer positions and colors without reload where the WebGL buffer is still available;
`globalThis.__riVisualControl.enable()` resumes the pre-render remap on the next draw.

## ARTIFACTS

- `workspace/evidence/flicker-before/trace.json`
- `workspace/evidence/flicker-before/metrics.json`
- `workspace/evidence/flicker-before/report.md`
- `workspace/evidence/flicker-after/trace.json`
- `workspace/evidence/flicker-after/metrics.json`
- `workspace/evidence/flicker-after/report.md`
- `workspace/evidence/flicker-live-after/trace.json`
- `workspace/evidence/flicker-live-after/metrics.json`
- `workspace/evidence/flicker-live-after/report.md`
