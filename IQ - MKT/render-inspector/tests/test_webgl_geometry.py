from __future__ import annotations

import base64
import struct

from render_inspector.inspector.webgl_geometry import analyze_webgl_frame, geometry_hits
from render_inspector.models import EvidenceStatus


def fixture() -> tuple[dict, dict]:
    frame = {
        "point": {"x": 50, "y": 50},
        "buffers": {
            "b@1": {
                "base64": base64.b64encode(
                    struct.pack("<6f", -0.8, -0.8, 0.8, -0.8, 0, 0.8)
                ).decode()
            }
        },
        "limitations": [],
    }
    draw = {
        "order": 0,
        "api": "drawArrays",
        "args": [4, 0, 3],
        "programId": "program",
        "shaders": [
            {"type": 35633, "source": "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}"}
        ],
        "attributes": [
            {
                "name": "p",
                "enabled": True,
                "size": 2,
                "type": 5126,
                "stride": 0,
                "offset": 0,
                "buffer": {"version": "b@1"},
            }
        ],
        "uniforms": [],
        "viewport": [0, 0, 100, 100],
        "scissorEnabled": False,
        "before": [0, 0, 0, 255],
        "after": [255, 0, 0, 255],
    }
    frame["draws"] = [draw]
    return frame, draw


def test_triangle_indices_are_spatial_not_temporal() -> None:
    frame, draw = fixture()
    assert geometry_hits(draw, frame)[0]["vertexIndices"] == [0, 1, 2]
    frame["point"] = {"x": 99, "y": 99}
    assert geometry_hits(draw, frame) == []


def test_scissor_excludes_geometry_and_unknown_shader_is_not_confirmed() -> None:
    frame, draw = fixture()
    draw.update(scissorEnabled=True, scissor=[0, 0, 10, 10])
    assert geometry_hits(draw, frame) == []
    draw["scissorEnabled"] = False
    draw["shaders"][0]["source"] = "attribute vec2 p;void main(){gl_Position=vec4(sin(p),0.,1.);}"
    result = analyze_webgl_frame(frame)
    assert result.status is EvidenceStatus.PROBABLE  # measured pixel contribution only
    assert not result.data["spatialMatches"]
    assert len(result.data["unsupportedDraws"]) == 1
    draw["after"] = draw["before"]
    assert analyze_webgl_frame(frame).status is EvidenceStatus.INCONCLUSIVE


def test_mat4_translation_and_index_buffer() -> None:
    frame, draw = fixture()
    draw["api"] = "drawElements"
    draw["args"] = [4, 3, 5123, 0]
    draw["indexBuffer"] = {"version": "i@1"}
    frame["buffers"]["i@1"] = {"base64": base64.b64encode(struct.pack("<3H", 2, 0, 1)).decode()}
    draw["shaders"][0]["source"] = (
        "attribute vec2 p;uniform mat4 m;void main(){gl_Position=m*vec4(p,0.,1.);}"
    )
    draw["uniforms"] = [
        {"name": "m", "type": 35676, "value": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0.1, 0, 0, 1]}
    ]
    hit = geometry_hits(draw, frame)[0]
    assert hit["vertexIndices"] == [2, 0, 1]
    assert abs(hit["screenTriangle"][0][0] - 55) < 1e-5


def test_flag_preprocessor_and_missing_attribute_components() -> None:
    frame, draw = fixture()
    draw["shaders"][0]["source"] = """#define AVAILABLE
#line 1
attribute vec4 p;
#ifndef UNUSED
varying vec2 uv;
#else
varying vec4 other;
#endif
void main(){gl_Position=vec4(p);uv=p.xy;}"""
    assert geometry_hits(draw, frame)[0]["vertexIndices"] == [0, 1, 2]
