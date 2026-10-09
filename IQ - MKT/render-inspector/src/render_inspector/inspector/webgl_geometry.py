"""Conservative CPU projection for a declared subset of WebGL vertex shaders.

No inferred shader semantics: unknown transforms, clipping and instancing stay unresolved.
Pixel changes are separate evidence of a draw's contribution, never component ownership.
"""

from __future__ import annotations

import base64
import math
import re
import struct
from typing import Any

from render_inspector.models import AnalysisCandidate, EvidenceStatus

TYPES = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5124: ("i", 4),
    5125: ("I", 4),
    5126: ("f", 4),
}


def _buffer(reference: dict[str, Any] | None, frame: dict[str, Any]) -> bytes:
    if not reference or reference.get("unavailable"):
        raise ValueError("Buffer was not available at draw time")
    value = frame.get("buffers", {}).get(reference.get("version"), reference)
    key = str(reference.get("version") or reference.get("id"))
    cache = frame.setdefault("_decodedBuffers", {})
    cached = cache.get(key)
    if isinstance(cached, bytes):
        return cached
    decoded = base64.b64decode(value["base64"], validate=True)
    cache[key] = decoded
    return decoded


def _attribute(
    attribute: dict[str, Any], index: int, frame: dict[str, Any], declared_size: int
) -> list[float]:
    if not attribute.get("enabled") or attribute.get("divisor"):
        raise ValueError("Constant or instanced attribute unsupported")
    code, width = TYPES[attribute["type"]]
    size = int(attribute["size"])
    stride = int(attribute["stride"]) or size * width
    offset = int(attribute["offset"]) + index * stride
    values = [
        float(v)
        for v in struct.unpack_from(
            "<" + code * size, _buffer(attribute.get("buffer"), frame), offset
        )
    ]
    if attribute.get("normalized") and code != "f":
        if code.islower():
            values = [max(-1.0, v / (2 ** (width * 8 - 1) - 1)) for v in values]
        else:
            values = [v / (2 ** (width * 8) - 1) for v in values]
    # Disabled/missing generic components follow the WebGL vertex attribute defaults.
    if declared_size > len(values):
        values.extend([0.0] * (declared_size - len(values)))
        if declared_size == 4:
            values[3] = 1.0
    return values


def _preprocess(source: str) -> str:
    """Resolve only flag-style GLSL directives; value/function macros fail closed."""
    defines: set[str] = set()
    active = [True]
    branches: list[tuple[bool, bool]] = []
    output = []
    for line in source.splitlines():
        match = re.match(r"\s*#\s*(\w+)(?:\s+(.*?))?\s*$", line)
        if not match:
            if active[-1]:
                output.append(line)
            continue
        directive, value = match[1], (match[2] or "").strip()
        if directive == "define":
            parts = value.split()
            if len(parts) != 1 or not re.fullmatch(r"\w+", parts[0]):
                raise ValueError("Value or function shader macros unsupported")
            if active[-1]:
                defines.add(parts[0])
        elif directive in {"ifdef", "ifndef"}:
            if not re.fullmatch(r"\w+", value):
                raise ValueError("Complex shader condition unsupported")
            condition = value in defines
            if directive == "ifndef":
                condition = not condition
            branches.append((active[-1], condition))
            active.append(active[-1] and condition)
        elif directive == "else":
            if not branches:
                raise ValueError("Unbalanced shader conditional")
            parent, condition = branches[-1]
            active[-1] = parent and not condition
            branches[-1] = (parent, not condition)
        elif directive == "endif":
            if not branches:
                raise ValueError("Unbalanced shader conditional")
            branches.pop()
            active.pop()
        elif directive in {"line", "version", "extension"}:
            continue
        else:
            raise ValueError(f"Shader directive #{directive} unsupported")
    if branches:
        raise ValueError("Unbalanced shader conditional")
    return "\n".join(output)


def _transform(draw: dict[str, Any], index: int, frame: dict[str, Any]) -> list[float]:
    program = frame.get("programs", {}).get(draw.get("programId"), {})
    shaders = draw.get("shaders") or program.get("shaders", [])
    source = next(s["source"] for s in shaders if s["type"] == 35633)
    source = _preprocess(re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S))
    if re.search(r"\b(if|for|while|switch|gl_VertexID|gl_InstanceID)\b", source):
        raise ValueError("Shader control flow or generated vertex IDs unsupported")
    assignments = re.findall(r"\bgl_Position\s*=\s*([^;]+);", source)
    if len(assignments) != 1 or re.search(r"gl_Position\s*(?:\.|\+=|-=|\*=|/=)", source):
        raise ValueError("Position is not a single supported assignment")
    expression = assignments[0].strip()
    # Support direct attributes or products of named mat4 uniforms and vec4 constructors.
    pieces = [piece.strip() for piece in expression.split("*")]
    operand = pieces[-1]
    match = re.fullmatch(r"vec4\(\s*(\w+)\s*((?:,\s*[-+]?\d+(?:\.\d*)?\s*)*)\)", operand)
    name = match[1] if match else operand
    main = re.search(r"void\s+main\s*\([^)]*\)\s*\{(.*)\}", source, flags=re.S)
    if not main or re.search(r"\b(?:float|int|vec[234]|mat[234])\s+", main[1]):
        raise ValueError("Local shader variables require an unsupported evaluator")
    attribute = next((a for a in draw["attributes"] if a["name"] == name), None)
    if attribute is None:
        raise ValueError("Position expression requires an unsupported shader operation")
    declared = re.search(
        rf"\battribute\s+(?:lowp\s+|mediump\s+|highp\s+)?(float|vec[234])\s+{re.escape(name)}\b",
        source,
    )
    if not declared:
        raise ValueError("Attribute declaration is unavailable")
    declared_size = 1 if declared[1] == "float" else int(declared[1][-1])
    vector = _attribute(attribute, index, frame, declared_size)
    if match:
        vector.extend(float(value) for value in match[2].split(",")[1:])
    if len(vector) != 4:
        raise ValueError("Position does not evaluate to vec4")
    for matrix_name in reversed(pieces[:-1]):
        uniform = next(
            (u for u in draw["uniforms"] if u["name"] == matrix_name and u["type"] == 35676), None
        )
        if uniform is None or len(uniform["value"]) != 16:
            raise ValueError("Transform is not a known mat4 uniform")
        matrix = uniform["value"]
        vector = [
            sum(float(matrix[col * 4 + row]) * vector[col] for col in range(4)) for row in range(4)
        ]
    if not all(math.isfinite(v) for v in vector) or vector[3] <= 0:
        raise ValueError("Non-finite or nonpositive clip-space w")
    if any(abs(v) > vector[3] for v in vector[:3]):
        raise ValueError("Primitive requires clip-space clipping")
    return vector


def _inside(point: tuple[float, float], triangle: list[list[float]]) -> bool:
    def cross(a: list[float], b: list[float]) -> float:
        return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])

    signs = [cross(triangle[i], triangle[(i + 1) % 3]) for i in range(3)]
    area = (triangle[1][0] - triangle[0][0]) * (triangle[2][1] - triangle[0][1]) - (
        triangle[1][1] - triangle[0][1]
    ) * (triangle[2][0] - triangle[0][0])
    return abs(area) > 1e-9 and (min(signs) >= -1e-9 or max(signs) <= 1e-9)


def geometry_hits(draw: dict[str, Any], frame: dict[str, Any]) -> list[dict[str, Any]]:
    if draw.get("framebufferId"):
        return []
    if draw["api"] not in {"drawArrays", "drawElements"}:
        raise ValueError("Instancing and extension draw APIs unsupported")
    args = draw["args"]
    mode = args[0]
    if mode not in {4, 5, 6}:
        raise ValueError("Only triangle primitives supported")
    px, py = float(frame["point"]["x"]) + 0.5, float(frame["point"]["y"]) + 0.5
    if draw.get("scissorEnabled"):
        sx, sy, sw, sh = draw["scissor"]
        if not (sx <= px < sx + sw and sy <= py < sy + sh):
            return []
    if draw["api"] == "drawArrays":
        indices = list(range(int(args[1]), int(args[1] + args[2])))
    else:
        code, width = TYPES[int(args[2])]
        if code not in {"B", "H", "I"}:
            raise ValueError("Unsupported element index type")
        count, offset = int(args[1]), int(args[3])
        if count > 60_000:
            raise ValueError("Index analysis budget exceeded")
        indices = list(
            struct.unpack_from("<" + code * count, _buffer(draw.get("indexBuffer"), frame), offset)
        )
    if len(indices) > 60_000:
        raise ValueError("Vertex analysis budget exceeded")
    if mode == 4:
        triangles = [indices[i : i + 3] for i in range(0, len(indices) - 2, 3)]
    elif mode == 5:
        triangles = [indices[i : i + 3] for i in range(len(indices) - 2)]
    else:
        triangles = [[indices[0], indices[i], indices[i + 1]] for i in range(1, len(indices) - 1)]
    viewport = draw["viewport"]
    vertices: dict[int, list[float]] = {}
    hits = []
    for primitive, ids in enumerate(triangles):
        screen = []
        for index in ids:
            if index not in vertices:
                clip = _transform(draw, index, frame)
                vertices[index] = [
                    viewport[0] + (clip[0] / clip[3] + 1) * viewport[2] / 2,
                    viewport[1] + (clip[1] / clip[3] + 1) * viewport[3] / 2,
                ]
            screen.append(vertices[index])
        if _inside((px, py), screen):
            hits.append({"primitive": primitive, "vertexIndices": ids, "screenTriangle": screen})
    return hits


def analyze_webgl_frame(frame: dict[str, Any]) -> AnalysisCandidate:
    matches, unsupported, changes = [], [], []
    for draw in frame.get("draws", []):
        before, after = draw.get("before"), draw.get("after")
        changed = before is not None and after is not None and before != after
        if changed:
            changes.append(
                {
                    "order": draw["order"],
                    "api": draw["api"],
                    "programId": draw.get("programId"),
                    "before": before,
                    "after": after,
                }
            )
        if draw["api"] == "clear":
            continue
        try:
            hits = geometry_hits(draw, frame)
            if hits:
                matches.append(
                    {
                        "order": draw["order"],
                        "programId": draw.get("programId"),
                        "hits": hits,
                        "pixelChanged": changed,
                        "stack": frame.get("stacks", {}).get(str(draw.get("stackId"))),
                        "rasterState": {
                            "blend": draw.get("blendEnabled"),
                            "depth": draw.get("depthEnabled"),
                            "stencil": draw.get("stencilEnabled"),
                            "cull": draw.get("cullEnabled"),
                        },
                    }
                )
        except (ValueError, KeyError, IndexError, StopIteration, struct.error, TypeError) as exc:
            unsupported.append({"order": draw["order"], "reason": str(exc)})
    contributing = [c for c in changes if c["api"] != "clear"]
    frame.pop("_decodedBuffers", None)
    return AnalysisCandidate(
        kind="WebGL frame / spatial evidence",
        status=EvidenceStatus.PROBABLE if matches or contributing else EvidenceStatus.INCONCLUSIVE,
        evidence=[
            f"{len(frame.get('draws', []))} commands captured ({frame.get('boundaryMode', 'boundary not specified')})",
            f"{len(matches)} draws have supported geometry covering the selected pixel",
            f"{len(contributing)} draw calls changed that pixel during execution",
            "Exclusive ownership and semantic component identity are not confirmed",
        ],
        data={
            "canvasId": frame.get("canvasId"),
            "point": frame.get("point"),
            "drawCount": len(frame.get("draws", [])),
            "spatialMatches": matches,
            "pixelChanges": changes,
            "unsupportedDraws": unsupported,
            "limitations": frame.get("limitations", []),
            "captureError": frame.get("error"),
        },
    )
