#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // RASTREADOR DE MOUSE & CLIQUE EM ALTA PRECISÃO
Captura a trajetória contínua do cursor e os eventos de clique mecânico
para renderização com overlay no vídeo vertical 9:16.
=============================================================================
"""

import time
import json
import threading
import ctypes
import ctypes.wintypes
from pathlib import Path

class MouseTracker:
    def __init__(self, fps=30):
        self.fps = fps
        self.interval = 1.0 / fps
        self.trajectory = []
        self.clicks = []
        self.stop_event = threading.Event()
        self.thread = None
        self.start_time = 0.0

    def _track_loop(self):
        user32 = ctypes.windll.user32
        pt = ctypes.wintypes.POINT()
        
        # Anexar à sessão interativa se utilitário disponível
        try:
            import sys
            sys.path.append(str(Path(__file__).parent.parent / "scripts"))
            from desktop_util import attach_to_default_desktop
            attach_to_default_desktop()
        except Exception:
            pass
            
        next_t = time.perf_counter()
        while not self.stop_event.is_set():
            now = time.perf_counter()
            if now >= next_t:
                elapsed = round(now - self.start_time, 3)
                user32.GetCursorPos(ctypes.byref(pt))
                self.trajectory.append({
                    "t": elapsed,
                    "x": int(pt.x),
                    "y": int(pt.y)
                })
                next_t += self.interval
            else:
                time.sleep(0.005)

    def start(self, start_perf_time=None):
        self.start_time = start_perf_time or time.perf_counter()
        self.stop_event.clear()
        self.trajectory = []
        self.clicks = []
        self.thread = threading.Thread(target=self._track_loop, daemon=True)
        self.thread.start()

    def record_click(self, x, y, action="CALL", t=None):
        click_t = t or (time.perf_counter() - self.start_time)
        self.clicks.append({
            "t": round(click_t, 3),
            "x": int(x),
            "y": int(y),
            "action": action
        })

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

    def save(self, filepath):
        filepath = Path(filepath).resolve()
        data = {
            "fps": self.fps,
            "clicks": self.clicks,
            "trajectory": self.trajectory
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return filepath

if __name__ == "__main__":
    tracker = MouseTracker(fps=30)
    tracker.start()
    time.sleep(1.0)
    tracker.record_click(1855, 465)
    time.sleep(0.5)
    tracker.stop()
    print("Amostras coletadas:", len(tracker.trajectory))
    print("Cliques registrados:", tracker.clicks)
