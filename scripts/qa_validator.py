#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // PORTÃO DE QUALIDADE (QA GATE) PRÉ-COMMIT
Valida integridade do vídeo MP4, consistência de FPS e contrato de telemetria.
=============================================================================
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
RAW_DIR = BASE_DIR / "raw_recordings"
QUARANTINE_DIR = BASE_DIR / "quarantine"
RAW_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

def inspect_video_stream(video_path):
    """Executes ffprobe to extract real stream metrics."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return None, "Nenhum stream de vídeo encontrado"
        return streams[0], None
    except Exception as e:
        return None, str(e)

def run_qa_gate(take_dir):
    take_dir = Path(take_dir).resolve()
    video_path = take_dir / "video_master.mp4"
    telemetry_path = take_dir / "telemetry.json"
    qa_report_path = take_dir / "qa_report.json"
    
    report = {
        "take_id": take_dir.name,
        "status": "PENDING",
        "checks": {},
        "errors": []
    }
    
    # Check 1: Existence of files
    if not video_path.exists():
        report["errors"].append("Arquivo video_master.mp4 não encontrado.")
    if not telemetry_path.exists():
        report["errors"].append("Arquivo telemetry.json não encontrado.")
        
    if report["errors"]:
        report["status"] = "FAILED"
        _commit_failed(take_dir, report)
        return False

    # Check 2: FFprobe Video Stream Validation
    stream_info, probe_err = inspect_video_stream(video_path)
    if probe_err or not stream_info:
        report["checks"]["ffprobe"] = {"passed": False, "error": probe_err}
        report["errors"].append(f"FFprobe falhou: {probe_err}")
    else:
        w = int(stream_info.get("width", 0))
        h = int(stream_info.get("height", 0))
        report["checks"]["ffprobe"] = {
            "passed": True,
            "width": w,
            "height": h,
            "r_frame_rate": stream_info.get("r_frame_rate"),
            "duration": stream_info.get("duration")
        }
        if w != 1920 or h != 1080:
            report["errors"].append(f"Resolução incorreta: {w}x{h} (esperado 1920x1080)")

    # Check 3: Telemetry Contract & Frame Drops
    try:
        with open(telemetry_path, "r", encoding="utf-8") as f:
            telemetry = json.load(f)
            
        session = telemetry.get("session", {})
        total_frames = session.get("total_frames", 0)
        duration_sec = session.get("duration_seconds", 0)
        target_fps = session.get("target_fps", 60.0)
        
        expected_frames = duration_sec * target_fps
        frame_diff = abs(total_frames - expected_frames)
        drop_rate = (frame_diff / expected_frames * 100.0) if expected_frames > 0 else 0.0
        
        report["checks"]["frame_consistency"] = {
            "passed": drop_rate <= 1.0,
            "total_frames": total_frames,
            "expected_frames": round(expected_frames, 1),
            "drop_rate_percent": round(drop_rate, 2)
        }
        
        if drop_rate > 1.0:
            report["errors"].append(f"Taxa de queda de quadros alta: {drop_rate:.2f}% (Tolerância máx: 1.0%)")
            
        actions = telemetry.get("actions", [])
        report["checks"]["actions_logged"] = {
            "passed": len(actions) >= 3,
            "count": len(actions)
        }
        if len(actions) < 3:
            report["errors"].append(f"Poucas ações de telemetria registradas ({len(actions)}). Esperado mínimo de 3.")
            
    except Exception as e:
        report["errors"].append(f"Falha ao validar telemetry.json: {e}")

    # Decision
    passed = len(report["errors"]) == 0
    report["status"] = "PASSED" if passed else "FAILED"
    
    with open(qa_report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    if passed:
        dest_dir = RAW_DIR / take_dir.name
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        shutil.move(str(take_dir), str(dest_dir))
        print(f"[QA GATE APROVADO] Take promovido para: {dest_dir}")
        return True
    else:
        _commit_failed(take_dir, report)
        return False

def _commit_failed(take_dir, report):
    dest_dir = QUARANTINE_DIR / take_dir.name
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.move(str(take_dir), str(dest_dir))
    print(f"[QA GATE REPROVADO] Take isolado em quarentena: {dest_dir}")
    print(f"Erros detectados: {report['errors']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Portão de QA para gravações do El Cazador del Wins")
    parser.add_argument("--take-dir", required=True, help="Caminho para o diretório do take em staging")
    args = parser.parse_args()
    run_qa_gate(args.take_dir)
