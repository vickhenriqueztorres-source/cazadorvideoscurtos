from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_extension_architecture() -> None:
    forbidden_files = {"manifest.json", "service-worker.js", "content-script.js"}
    project_files = [path for path in ROOT.rglob("*") if "workspace" not in path.parts]
    assert not any(path.name.lower() in forbidden_files for path in project_files)
    forbidden_tokens = ("chrome.runtime", "chrome.tabs", "chrome.scripting")
    for path in [item for item in project_files if item.suffix in {".py", ".js"}]:
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        assert all(token not in text for token in forbidden_tokens), path
