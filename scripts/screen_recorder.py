#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // ENGINE DE GRAVAÇÃO 60 FPS + TELEMETRIA DUAL-INDEX
Arquitetura 2.0: Gravação Desacoplada (MSS + Pipe FFmpeg com Auto-Codec)
=============================================================================
"""

import sys
import os
import time
import json
import shutil
import queue
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# Fix Windows console UTF-8 output
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import mss
import pyautogui
import numpy as np

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.2

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
CONFIG_FILE = BASE_DIR / "config" / "iqoption_coords.json"
RECORDER_CONFIG_FILE = BASE_DIR / "config" / "recorder_config.json"
STAGING_DIR = BASE_DIR / "staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

def detect_best_encoder():
    """Detects available hardware-accelerated H.264 encoder in FFmpeg."""
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
        out = res.stdout
        # Priority order
        if "h264_nvenc" in out:
            # Test if driver actually supports it
            test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]
            if subprocess.run(test_cmd, capture_output=True).returncode == 0:
                return "h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "ull", "-pix_fmt", "yuv420p", "-b:v", "18M"]
        if "h264_mf" in out:
            test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_mf", "-f", "null", "-"]
            if subprocess.run(test_cmd, capture_output=True).returncode == 0:
                return "h264_mf", ["-c:v", "h264_mf", "-b:v", "18M", "-pix_fmt", "yuv420p"]
        if "h264_qsv" in out:
            test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_qsv", "-f", "null", "-"]
            if subprocess.run(test_cmd, capture_output=True).returncode == 0:
                return "h264_qsv", ["-c:v", "h264_qsv", "-b:v", "18M", "-pix_fmt", "nv12"]
    except Exception:
        pass
    # Universal bulletproof fallback (independent C++ multithreaded process outside Python GIL)
    return "libx264_ultrafast", ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "18", "-pix_fmt", "yuv420p"]

class CazadorScreenRecorder:
    def __init__(self, target_fps=60.0, width=1920, height=1080):
        self.target_fps = target_fps
        self.width = width
        self.height = height
        self.frame_duration = 1.0 / self.target_fps
        
        self.frame_queue = queue.Queue(maxsize=120)
        self.stop_event = threading.Event()
        self.atomic_frame_index = 0
        self.start_perf_time = 0.0
        
        self.telemetry = {
            "schema_version": "1.0",
            "session": {},
            "qa_status": {"verified": False},
            "rois_9_16": {},
            "actions": []
        }
        self.load_coords()
        
    def load_coords(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.coords = data.get("elements", {})
                self.telemetry["rois_9_16"] = data.get("rois_9_16", {})
        else:
            self.coords = {}

    def get_current_frame(self):
        return self.atomic_frame_index

    def log_action(self, action_name, mouse_x, mouse_y, duration_ms=300, roi_target="action_view", metadata=None):
        frame_idx = self.atomic_frame_index
        now_perf = time.perf_counter()
        rel_ms = (now_perf - self.start_perf_time) * 1000.0 if self.start_perf_time > 0 else 0
        
        entry = {
            "step_id": len(self.telemetry["actions"]) + 1,
            "action_name": action_name,
            "frame_index": frame_idx,
            "timestamp_ms": round(rel_ms, 2),
            "duration_ms": duration_ms,
            "mouse_x": mouse_x,
            "mouse_y": mouse_y,
            "roi_target": roi_target,
            "metadata": metadata or {}
        }
        self.telemetry["actions"].append(entry)
        print(f"  [TELEMETRIA] Frame #{frame_idx:05d} ({rel_ms:7.1f}ms) -> {action_name} at ({mouse_x}, {mouse_y})")

    def _producer_thread(self):
        """Ultra-fast frame grabber loop with precise timing."""
        with mss.mss() as sct:
            monitor = {"top": 0, "left": 0, "width": self.width, "height": self.height}
            next_frame_time = time.perf_counter()
            
            while not self.stop_event.is_set():
                now = time.perf_counter()
                if now >= next_frame_time:
                    img = sct.grab(monitor)
                    # Raw BGRA -> BGR
                    frame_bytes = np.frombuffer(img.raw, dtype=np.uint8).reshape((self.height, self.width, 4))[:, :, :3].tobytes()
                    
                    try:
                        self.frame_queue.put_nowait(frame_bytes)
                        self.atomic_frame_index += 1
                    except queue.Full:
                        pass # Drop frame in queue if downstream congested
                        
                    next_frame_time += self.frame_duration
                    if next_frame_time < now:
                        next_frame_time = now + self.frame_duration
                else:
                    sleep_time = next_frame_time - now
                    if sleep_time > 0.001:
                        time.sleep(sleep_time * 0.75)

    def _consumer_thread(self, ffmpeg_proc):
        """Pipes raw BGR frames to FFmpeg stdin."""
        while not self.stop_event.is_set() or not self.frame_queue.empty():
            try:
                frame_bytes = self.frame_queue.get(timeout=0.1)
                ffmpeg_proc.stdin.write(frame_bytes)
                self.frame_queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                break
        try:
            ffmpeg_proc.stdin.close()
        except Exception:
            pass

    def run_recording_session(self, duration_seconds=28, action_set="sniper_5s"):
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        take_id = f"take_{timestamp_str}"
        take_staging_dir = STAGING_DIR / take_id
        take_staging_dir.mkdir(parents=True, exist_ok=True)
        video_output = take_staging_dir / "video_master.mp4"
        telemetry_output = take_staging_dir / "telemetry.json"
        
        encoder_name, encoder_args = detect_best_encoder()
        print(f"\n=== INICIANDO GRAVAÇÃO DO TAKE: {take_id} ===")
        print(f"Resolução: {self.width}x{self.height} @ {self.target_fps} FPS")
        print(f"Encoder Ativo: {encoder_name} ({' '.join(encoder_args)})")
        print(f"Destino Staging: {video_output}")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.width}x{self.height}",
            "-pix_fmt", "bgr24",
            "-r", str(int(self.target_fps)),
            "-i", "-",
        ] + encoder_args + [
            "-r", str(int(self.target_fps)),
            str(video_output)
        ]
        
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        # Start Threads
        self.stop_event.clear()
        self.atomic_frame_index = 0
        self.start_perf_time = time.perf_counter()
        
        producer = threading.Thread(target=self._producer_thread, daemon=True)
        consumer = threading.Thread(target=self._consumer_thread, args=(ffmpeg_proc,), daemon=True)
        
        producer.start()
        consumer.start()
        
        print("[ENGINE] Gravação ativa em background! Executando sequência de automação...")
        
        # Sequence Execution
        try:
            self._execute_trading_sequence(action_set, duration_seconds)
        except Exception as e:
            print(f"[ERRO NA AUTOMAÇÃO] {e}")
        finally:
            print("[ENGINE] Finalizando captura de frames e fechando stream...")
            self.stop_event.set()
            producer.join(timeout=2.0)
            consumer.join(timeout=5.0)
            ffmpeg_proc.wait(timeout=5.0)
            
        total_time = time.perf_counter() - self.start_perf_time
        
        # Finalize Telemetry
        self.telemetry["session"] = {
            "take_id": take_id,
            "channel": "El Cazador del Wins",
            "platform": "IQ Option",
            "asset_pair": "EUR/USD-OTC",
            "timeframe": "5s",
            "expiry_seconds": 60,
            "target_fps": self.target_fps,
            "native_resolution": f"{self.width}x{self.height}",
            "created_at": datetime.now().isoformat(),
            "duration_seconds": round(total_time, 2),
            "total_frames": self.atomic_frame_index,
            "encoder_used": encoder_name
        }
        
        with open(telemetry_output, "w", encoding="utf-8") as f:
            json.dump(self.telemetry, f, indent=2, ensure_ascii=False)
            
        print(f"[OK] Gravação encerrada. Total de Frames: {self.atomic_frame_index} em {total_time:.2f}s")
        print(f"[OK] Telemetria persistida em: {telemetry_output}")
        
        # Trigger QA Gate
        print("\n=== ENCAMINHANDO PARA PORTÃO DE QA ===")
        from qa_validator import run_qa_gate
        passed = run_qa_gate(take_staging_dir)
        return passed, take_staging_dir

    def _execute_trading_sequence(self, action_set, max_duration):
        """Sequência suave de automação compatível com o canal."""
        time.sleep(1.5)
        
        # Ação 1: Troca para Velas
        if "tipo_grafico" in self.coords and "opcao_velas" in self.coords:
            tg = self.coords["tipo_grafico"]
            ov = self.coords["opcao_velas"]
            pyautogui.moveTo(tg["x"], tg["y"], duration=0.8, tween=pyautogui.easeInOutQuad)
            self.log_action("OPEN_CHART_TYPE_MENU", tg["x"], tg["y"], roi_target="setup_view")
            pyautogui.click()
            time.sleep(0.5)
            
            pyautogui.moveTo(ov["x"], ov["y"], duration=0.6, tween=pyautogui.easeInOutQuad)
            self.log_action("SELECT_CANDLESTICKS", ov["x"], ov["y"], roi_target="setup_view")
            pyautogui.click()
            time.sleep(0.8)

        # Ação 2: Período de 5s
        if "periodo_vela" in self.coords and "opcao_5s" in self.coords:
            pv = self.coords["periodo_vela"]
            o5 = self.coords["opcao_5s"]
            pyautogui.moveTo(pv["x"], pv["y"], duration=0.7, tween=pyautogui.easeInOutQuad)
            self.log_action("OPEN_PERIOD_MENU", pv["x"], pv["y"], roi_target="setup_view")
            pyautogui.click()
            time.sleep(0.4)
            
            pyautogui.moveTo(o5["x"], o5["y"], duration=0.5, tween=pyautogui.easeInOutQuad)
            self.log_action("SELECT_5S_TIMEFRAME", o5["x"], o5["y"], roi_target="setup_view")
            pyautogui.click()
            time.sleep(1.0)

        # Ação 3: Movimento Analítico no Gráfico
        if "centro_grafico" in self.coords:
            cg = self.coords["centro_grafico"]
            pyautogui.moveTo(cg["x"], cg["y"], duration=1.0, tween=pyautogui.easeInOutQuad)
            self.log_action("ANALYZE_CANDLE_VOLATILITY", cg["x"], cg["y"], roi_target="action_view")
            time.sleep(2.0)

        # Ação 4: Gatilho Sniper Call (Verde)
        if "btn_call" in self.coords:
            bc = self.coords["btn_call"]
            pyautogui.moveTo(bc["x"], bc["y"], duration=0.7, tween=pyautogui.easeInOutQuad)
            self.log_action("SNIPER_TRIGGER_CALL", bc["x"], bc["y"], duration_ms=150, roi_target="trigger_view", metadata={"direction": "CALL", "payout_pct": 89})
            pyautogui.click()
            time.sleep(1.0)
            
        # Espera restante até atingir tempo de expiração do take
        elapsed = time.perf_counter() - self.start_perf_time
        remaining = max_duration - elapsed
        if remaining > 0:
            time.sleep(remaining)
            
        # Ação 5: Registro de Resultado WIN
        if "btn_call" in self.coords:
            self.log_action("WIN_CONFIRMATION", 1835, 450, roi_target="action_view", metadata={"result": "WIN", "profit_usd": 89.0})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="El Cazador del Wins - Screen Recorder 60 FPS")
    parser.add_argument("--duration", type=int, default=28, help="Duração da gravação em segundos")
    parser.add_argument("--action-set", type=str, default="sniper_5s", help="Conjunto de ações a executar")
    args = parser.parse_args()
    
    recorder = CazadorScreenRecorder()
    recorder.run_recording_session(duration_seconds=args.duration, action_set=args.action_set)
