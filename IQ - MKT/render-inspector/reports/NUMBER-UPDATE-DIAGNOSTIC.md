# Number update diagnostic

Date: 2026-09-17  
Target: IQ Option traderoom

## Outcome

The stale-number behavior has two different answers depending on the surface:

1. **Header balance:** no freeze caused by the vertex remap was observed. The header rendered
   `$10,003.55` after loading, and the source glyph streams did not supply a subsequent value during
   the observation window.
2. **Account menu balances:** confirmed frozen by the current implementation. The menu is a cached
   pixel snapshot rather than a continuously rendered source.

## Header balance evidence

- Composited frames captured: 122
- Visible header number states: loading/empty, then `$10,003.55`
- Source-value changes after each draw source's baseline: 0
- Presented number changes after the header appeared: 0
- Account pixel overlay active: no
- Header renderer: live `#glcanvas` WebGL vertex path

The diagnostic initially saw alternating hashes, but these came from distinct draw calls with
different vertex counts. After grouping by program, buffer, draw arguments, and vertex count, every
source remained stable after its baseline. Therefore the renderer was not given a second balance
value during this window. A static header was expected for this sample.

## Account menu evidence

Immediately after opening the menu:

- pixel snapshot hash: `839307325`
- capture timestamp: `21176.8 ms`
- capture count: `1`
- renderer draw serial: `19273`

After 2.5 seconds:

- pixel snapshot hash: `839307325`
- capture timestamp: `21176.8 ms`
- capture count: `1`
- renderer draw serial: `25156`

The renderer executed 5,883 more draws while the menu image, capture time, and capture count remained
unchanged. This confirms that the menu cannot show real-time number changes while open.

## Root cause

`hooks/webgl-editor.js` computes `menuNeedsCapture` as true only when there is no existing
`__riMenuPixels` snapshot or the menu is in its opening phase. Once the first capture succeeds,
`__riMenuPixels` exists and `__riMenuOpening` becomes false, so no further `readPixels` capture occurs.

The captured image is also assigned to `__riMenuCachedPixels`. On a later menu opening, the cached
pixels are reused whenever the canvas dimensions match.

`hooks/webgl-overlay.js` then creates a new `ImageData` from this same frozen byte array and paints it
with `putImageData`. Refreshing the overlay does not refresh the source pixels; it only paints the
same snapshot again.

The effective pipeline is:

```text
menu opens
→ WebGL menu is captured once
→ pixel values are rearranged/recolored
→ snapshot is cached
→ same ImageData is presented repeatedly
→ underlying renderer continues changing independently
```

This is a data freshness bug, not an FPS problem.

## Correct fix layer

The preferred correction is to stop representing menu balances as captured pixels. The account menu
should be remapped at its WebGL source/draw layer, allowing the original renderer to continue drawing
the current numbers every frame or whenever its state changes.

An interim fallback could recapture on every detected menu-state change, but it would remain a
post-render overlay and would retain synchronization/flicker risk. It is not the preferred final
architecture.

## Evidence

- `workspace/evidence/number-update-diagnostic/metrics.json`
- `workspace/evidence/number-update-diagnostic/header-number-state-01.png`
- `workspace/evidence/number-update-diagnostic/header-number-state-02.png`
