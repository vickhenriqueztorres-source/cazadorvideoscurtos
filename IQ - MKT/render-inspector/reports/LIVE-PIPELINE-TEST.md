# Live pipeline test

Date: 2026-09-17  
Target: `https://iqoption.com/traderoom`  
Viewport: 1920×945

## Result

`NO_FLICKER_OBSERVED_AND_ALL_DISCOVERED_WEBGL_CONTEXTS_HOOKED`

The test inspected renderer inputs, pre-draw state, every discovered graphics context, worker targets,
and composited pixels delivered through Chrome's screencast path.

## Presented-frame test

- Requested composited frames: 120
- Captured composited frames: 122
- Frames containing the orange source color in the header target region: 0
- Maximum orange pixels in the target region: 0
- Frames containing the expected green state: 121
- The remaining frame was the platform connection/loading screen before the header was present

This is stronger than checking the WebGL hook alone: these images came from the browser's composed
page output after renderer layers were combined.

## Renderer trace

- Observable render cycles: 433
- Incorrect state at draw: 0 frames
- Post-render overrides: 0 frames
- Reference/target maximum motion delta: 0 px
- Average override duration: 0.0692 ms
- Dropped trace events: 0
- Classification: none
- Status: PASS, Grade B

The page recreated/uploaded graphical state throughout the trace. No later frame overwrote the
target with the original orange state.

## Context and layer inventory

Five graphics contexts were created in the main document:

| Context | Element | Type | Size | Main hook | Editor rule |
|---|---|---:|---:|---:|---:|
| `context_0001` | hidden canvas | Canvas2D | 300×150 | yes | not applicable |
| `context_0002` | hidden canvas | Canvas2D | 300×150 | yes | not applicable |
| `context_0003` | hidden canvas | WebGL | 300×150 | yes | no |
| `context_0004` | `#glcanvas` | WebGL | 1920×945 | yes | `real-header-match-demo` |
| `context_0005` | hidden canvas | Canvas2D | 16×16 | yes | not applicable |

Only `#glcanvas` was visible and full-screen. No discovered WebGL context lacked the diagnostic hook.
The other WebGL context was a hidden 300×150 canvas and could not present the header.

The dedicated Worker and Service Worker both received the early runtime hook. Neither created a
Canvas, OffscreenCanvas context, WebGL context, or Canvas2D context during the test. Therefore
`WORKER_MAIN_THREAD_DESYNC` was not supported by the evidence.

## Hypothesis matrix

| Hypothesis | Test | Result |
|---|---|---|
| Orange enters vertex buffer | Inspect final vertex/color state before every candidate draw | Not present at native draw |
| Orange comes from a uniform | Inspect renderer type and state | Live header uses interleaved `a_color`; no incorrect uniform draw observed |
| Icon comes from texture/UV | Inspect target vertices and composed output | Target alpha suppressed before draw; icon absent |
| Target is one frame behind reference | Compare same-frame desired and effective position | Maximum delta 0 px |
| Correction runs after `drawElements` | Order override and native draw timestamps | 0 post-render frames |
| Hook starts too late | Inventory contexts created after early-document bootstrap | Visible WebGL context has runtime, WebGL, and editor hooks |
| Next frame overwrites correction | Observe hundreds of successive render cycles | 0 incorrect draws across 433 cycles |
| Another canvas presents orange | Inventory all canvases and scan composited frames | One visible canvas; 0 orange presented frames |
| Worker/OffscreenCanvas presents orange | Inspect attached worker runtimes | Workers instrumented; 0 graphics contexts |
| Browser compositor exposes orange | Scan Chrome screencast frames | 0/122 frames contained source orange in target region |

## Interpretation

During this test window, none of the listed failure modes occurred. The modification reached the
correct visible WebGL context before its native draw, survived subsequent renders, and the incorrect
orange state did not appear in the composed frames.

This result does not prove that an intermittent event which did not occur during the window is
impossible. If the reported flicker happens only during a particular action—account switch, menu
opening, balance update, reconnect, or resize—the same test must remain armed while that exact event
is reproduced. The test command is:

```powershell
python tools/test_live_pipeline.py --frames 120 --timeout 18
```

## Evidence

- `workspace/evidence/live-pipeline-test/metrics.json`
- `workspace/evidence/live-pipeline-test/presented-frames.json`
- `workspace/evidence/live-pipeline-test/trace.json`
- `workspace/evidence/live-pipeline-test/inventory-before.json`
- `workspace/evidence/live-pipeline-test/inventory-after.json`
- `workspace/evidence/live-pipeline-test/targets.json`
