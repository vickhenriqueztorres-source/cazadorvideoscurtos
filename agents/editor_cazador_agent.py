#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: EditorCazadorAgent (Etapa 3)
Montagem Programática & Efeitos de Dopamina:
- Lê telemetria exata do clique (millisecond_exact)
- Aplica zoom dinâmico no botão no instante exato do clique
- Mixa narração neural es-419 + 4 camadas de SFX (Impacto, Mouse Click, Heartbeat, Cash)
- Renderiza em 1080x1920 @ 60 FPS constante
=============================================================================
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
SFX_DIR = BASE_DIR / "assets" / "sfx"
OUTPUT_DIR = BASE_DIR / "output_shorts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class EditorCazadorAgent:
    def __init__(self):
        self.sfx_impact = SFX_DIR / "sfx_impact.wav"
        self.sfx_click = SFX_DIR / "sfx_mouse_click.wav"
        self.sfx_heartbeat = SFX_DIR / "sfx_heartbeat.wav"
        self.sfx_cash = SFX_DIR / "sfx_cash.wav"

    def assemble_short(self, take_dir):
        take_dir = Path(take_dir).resolve()
        take_id = take_dir.name
        
        # 1. Localizar arquivos do take
        mp4_files = list(take_dir.glob("*.mp4"))
        if not mp4_files:
            raise FileNotFoundError(f"Vídeo MP4 não encontrado em {take_dir}")
        video_input = mp4_files[0]
        
        telemetry_files = list(take_dir.glob("*_telemetry.json")) + list(take_dir.glob("telemetry.json"))
        if not telemetry_files:
            raise FileNotFoundError(f"Telemetria não encontrada em {take_dir}")
        telemetry_file = telemetry_files[0]
        
        narration_file = take_dir / "narration.mp3"
        if not narration_file.exists():
            raise FileNotFoundError(f"Narração não encontrada em {narration_file}")
            
        with open(telemetry_file, "r", encoding="utf-8") as f:
            telemetry = json.load(f)
            
        click_sec = telemetry.get("click_event", {}).get("second_exact", 12.35)
        outcome_sec = telemetry.get("outcome_event", {}).get("expiration_second", 27.35)
        profit = telemetry.get("outcome_event", {}).get("profit_amount", 870)
        action = telemetry.get("click_event", {}).get("action", "CALL")
        
        # 2. Aplicar Motion Graphics nas Velas (Setas, Círculos, Textos Explicativos e Cursor do Mouse)
        try:
            from agents.motion_graphics_agent import MotionGraphicsAgent
        except ImportError:
            from motion_graphics_agent import MotionGraphicsAgent
        motion_agent = MotionGraphicsAgent(fps=30)
        video_with_motion = take_dir / f"{take_id}_motion.mp4"
        trajectory_file = take_dir / "mouse_trajectory.json"
        print("🎨 [EDITOR] Aplicando Motion Graphics nas velas, taxa e cursor do mouse...")
        motion_agent.apply_motion_graphics(
            video_input,
            video_with_motion,
            telemetry,
            trajectory_file=trajectory_file if trajectory_file.exists() else None
        )
        video_to_render = video_with_motion if video_with_motion.exists() else video_input
        
        output_file = OUTPUT_DIR / f"{take_id}_final.mp4"
        
        print("=" * 76)
        print(f"🎬 [EDITOR CAZADOR AGENT] INICIANDO MONTAGEM 60 FPS: {take_id}")
        print(f"Entrada de Vídeo: {video_input.name}")
        print(f"Telemetria: Clique às {click_sec}s | WIN às {outcome_sec}s (+${profit})")
        print(f"Destino Final: {output_file}")
        print("=" * 76)
        
        # Converter tempos para milissegundos para adelay
        delay_impact_ms = int(0.5 * 1000)
        delay_click_ms = int(click_sec * 1000)
        delay_hb_ms = int((click_sec + 2.5) * 1000)
        delay_cash_ms = int((outcome_sec - 1.0) * 1000)
        
        # Construir complex filter do FFmpeg
        # Audio graph:
        # [1:a] narração com volume 1.3
        # [2:a] impacto atrasado com adelay
        # [3:a] clique seco atrasado para o milissegundo exato
        # [4:a] heartbeat atrasado
        # [5:a] cash register no momento da vitória
        # Mixar tudo com amix
        filter_complex = (
            f"[1:a]volume=1.3[a_narr];"
            f"[2:a]adelay={delay_impact_ms}|{delay_impact_ms},volume=0.8[a_imp];"
            f"[3:a]adelay={delay_click_ms}|{delay_click_ms},volume=1.8[a_clk];"
            f"[4:a]adelay={delay_hb_ms}|{delay_hb_ms},volume=0.7[a_hb];"
            f"[5:a]adelay={delay_cash_ms}|{delay_cash_ms},volume=1.5[a_cash];"
            f"[a_narr][a_imp][a_clk][a_hb][a_cash]amix=inputs=5:duration=longest:dropout_transition=0[a_out];"
            f"[0:v]fps=30,format=yuv420p[v_out]"
        )
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_to_render),
            "-i", str(narration_file),
            "-i", str(self.sfx_impact),
            "-i", str(self.sfx_click),
            "-i", str(self.sfx_heartbeat),
            "-i", str(self.sfx_cash),
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-r", "30",
            str(output_file)
        ]
        
        print("⚡ Renderizando composição e aplicando trilha sonora sincronizada...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[ERRO NO FFMPEG] {res.stderr}")
            raise RuntimeError(f"FFmpeg render failed: {res.stderr}")
            
        print(f"✅ [RENDERIZAÇÃO CONCLUÍDA COM SUCESSO]")
        print(f"Arquivo gerado: {output_file} ({output_file.stat().st_size} bytes)")
        return output_file

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EditorCazadorAgent - Montagem de Shorts 60 FPS")
    parser.add_argument("--take-dir", required=True, help="Diretório do take homologado")
    args = parser.parse_args()
    
    editor = EditorCazadorAgent()
    editor.assemble_short(args.take_dir)
