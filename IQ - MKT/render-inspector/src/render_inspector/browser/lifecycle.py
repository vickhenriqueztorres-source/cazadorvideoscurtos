from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OwnedBrowser:
    process: subprocess.Popen[bytes]
    profile: Path
    port: int
    websocket_path: str

    @property
    def websocket_url(self) -> str:
        return f"ws://127.0.0.1:{self.port}{self.websocket_path}"

    async def close(self) -> None:
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            await asyncio.wait_for(asyncio.to_thread(self.process.wait), timeout=8)
        except TimeoutError:
            self.process.kill()
            await asyncio.to_thread(self.process.wait)


async def launch_browser(
    executable: Path, profile: Path, *, headless: bool = False
) -> OwnedBrowser:
    profile.mkdir(parents=True, exist_ok=True)
    active_port = profile / "DevToolsActivePort"
    if active_port.exists():
        active_port.unlink()
    args = [
        str(executable),
        f"--user-data-dir={profile}",
        "--remote-debugging-port=0",
        "--remote-debugging-address=127.0.0.1",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "--disable-background-networking",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=CalculateNativeWinOcclusion",
        "--disable-component-update",
        "about:blank",
    ]
    if headless:
        args.insert(-1, "--headless=new")
        args.insert(-1, "--disable-gpu-sandbox")
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    for _ in range(120):
        if process.poll() is not None:
            error = b"" if process.stderr is None else process.stderr.read()
            raise RuntimeError(
                f"browser exited before CDP startup: {error.decode(errors='replace')}"
            )
        if active_port.is_file():
            lines = active_port.read_text(encoding="utf-8").splitlines()
            if len(lines) >= 2:
                path = lines[1] if lines[1].startswith("/") else f"/{lines[1]}"
                return OwnedBrowser(process, profile, int(lines[0]), path)
        await asyncio.sleep(0.05)
    process.terminate()
    raise TimeoutError(f"DevToolsActivePort was not created in {profile}")
