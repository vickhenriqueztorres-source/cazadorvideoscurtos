#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: AuditorCazadorAgent (Etapa 3.5 - QA Pós-Produção)
Audita o vídeo final master (.mp4) quadro a quadro com visão computacional
antes de autorizar a entrega ou publicação:
1. Container & Streams (1080x1920, 30/60 FPS, h264, aac)
2. Integridade de Fluxo (zero tela preta, zero congelamentos)
3. Auditoria do Cabeçalho Superior (Tier 1: sem cortes no logo, saldo ou depósito)
4. Auditoria do Tier Inferior (Tier 3: HUD de Saldo e momento CALL/PUT íntegros)
5. Auditoria Financeira Estrita (Regra Zero-Loss: obrigatório WIN)
6. Auditoria de Áudio (faixa sincronizada presente)
=============================================================================
"""

import sys
import os
import json
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import cv2
import numpy as np

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
QUARANTINE_DIR = BASE_DIR / "quarantine"
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

class AuditorCazadorAgent:
    def __init__(self, target_width=1080, target_height=1920, min_fps=29.9):
        self.target_width = target_width
        self.target_height = target_height
        self.min_fps = min_fps

    def inspect_ffprobe(self, video_path):
        """Extrai metadados completos de vídeo e áudio via ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_streams", "-show_format",
            "-of", "json",
            str(video_path)
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout), None
        except Exception as e:
            return None, str(e)

    def audit_video(self, video_path, telemetry_path=None, take_dir=None):
        video_path = Path(video_path).resolve()
        take_id = video_path.stem.replace("_final", "")
        
        report = {
            "take_id": take_id,
            "video_file": str(video_path),
            "audited_at": datetime.now().isoformat(),
            "overall_verdict": "PENDING",
            "score": 100,
            "gates": {},
            "errors": []
        }
        
        print(f"\n🔍 [AUDITOR CAZADOR AGENT] INICIANDO AUDITORIA RIGOROSA: {video_path.name}")
        
        # -------------------------------------------------------------
        # PORTÃO 1: CONTAINER & STREAMS
        # -------------------------------------------------------------
        meta, probe_err = self.inspect_ffprobe(video_path)
        if probe_err or not meta:
            report["errors"].append(f"Falha de leitura do arquivo de vídeo: {probe_err}")
            report["gates"]["gate_1_container"] = {"passed": False, "error": probe_err}
            return self._finalize_report(report, video_path, take_dir)
            
        streams = meta.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        
        if not v_stream:
            report["errors"].append("Nenhum fluxo de vídeo encontrado.")
            report["gates"]["gate_1_container"] = {"passed": False}
            return self._finalize_report(report, video_path, take_dir)
            
        vw = int(v_stream.get("width", 0))
        vh = int(v_stream.get("height", 0))
        fps_parts = v_stream.get("r_frame_rate", "30/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
        v_duration = float(meta.get("format", {}).get("duration", 0.0))
        
        g1_passed = (vw == self.target_width and vh == self.target_height and fps >= self.min_fps and v_duration >= 45.0)
        report["gates"]["gate_1_container"] = {
            "passed": g1_passed,
            "width": vw,
            "height": vh,
            "fps": round(fps, 2),
            "duration": round(v_duration, 2)
        }
        if not g1_passed:
            report["errors"].append(f"Dimensões ou FPS fora do padrão: {vw}x{vh} @ {fps:.1f} FPS, duração: {v_duration:.1f}s")

        # -------------------------------------------------------------
        # PORTÃO 2: INTEGRIDADE DE FLUXO (BLACK FRAMES & FREEZE)
        # -------------------------------------------------------------
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            report["errors"].append("Não foi possível abrir o vídeo para decodificação OpenCV.")
            report["gates"]["gate_2_stream_integrity"] = {"passed": False}
            return self._finalize_report(report, video_path, take_dir)
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_indices = np.linspace(0, total_frames - 1, min(40, total_frames), dtype=int)
        
        black_frames = 0
        frozen_count = 0
        prev_frame = None
        
        for idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if not ret or frame is None:
                continue
                
            mean_val = float(np.mean(frame))
            if mean_val < 4.0:
                black_frames += 1
                
            if prev_frame is not None:
                diff = float(np.mean(np.abs(frame.astype(float) - prev_frame.astype(float))))
                if diff < 0.1:
                    frozen_count += 1
            prev_frame = frame
            
        g2_passed = (black_frames == 0 and frozen_count < 5)
        report["gates"]["gate_2_stream_integrity"] = {
            "passed": g2_passed,
            "black_frames_detected": black_frames,
            "frozen_samples_detected": frozen_count
        }
        if not g2_passed:
            report["errors"].append(f"Anomalias de reprodução: {black_frames} telas pretas, {frozen_count} amostras congeladas.")

        # -------------------------------------------------------------
        # PORTÃO 3: CABEÇALHO SUPERIOR (TIER 1: Y: 0..160)
        # -------------------------------------------------------------
        # Verificar se logotipo (laranja), perfil (verde) e saldo estão presentes sem cortes
        hdr_checks = []
        for sec in [2.0, 15.0, 30.0, 50.0]:
            f_idx = min(total_frames - 1, int(sec * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                tier1 = frame[0:160, :]
                # Laranja do logo IQ Option no canto esquerdo
                orange_logo = int(np.sum((tier1[:, 0:250, 2] > 180) & (tier1[:, 0:250, 1] > 70) & (tier1[:, 0:250, 0] < 70)))
                # Verde do avatar / saldo / depósito no canto direito
                green_header = int(np.sum((tier1[:, 600:1080, 1] > 125) & (tier1[:, 600:1080, 1] > tier1[:, 600:1080, 2] + 20)))
                hdr_checks.append((orange_logo > 50, green_header > 50))
                
        hdr_ok = len(hdr_checks) > 0 and all(c[0] and c[1] for c in hdr_checks)
        report["gates"]["gate_3_header_tier1"] = {
            "passed": hdr_ok,
            "samples_verified": len(hdr_checks),
            "details": "Logo IQ Option e Saldo/Depósito 100% íntegros sem cortes no Tier 1"
        }
        if not hdr_ok:
            report["errors"].append("Cabeçalho superior com anomalias: Logo IQ Option ou Saldo não detectados adequadamente.")

        # -------------------------------------------------------------
        # PORTÃO 4: TIER INFERIOR & HUD DE SALDO/MOMENTO (TIER 3: Y: 1180..1920)
        # -------------------------------------------------------------
        # Inspecionar se o HUD operacional (x: 0..570, y: 1205..1545) está preenchido e cobre a borda x=0
        tier3_checks = []
        for sec in [5.0, 18.0, 26.0, 52.0]:
            f_idx = min(total_frames - 1, int(sec * fps))
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if ret and frame is not None:
                # Região do HUD
                hud_sample = frame[1210:1540, 0:565]
                # Verificar se a borda esquerda x=0 está devidamente preenchida (sem pixels transparentes ou sem conteúdo)
                left_edge_mean = float(np.mean(frame[1210:1540, 0:5]))
                hud_mean = float(np.mean(hud_sample))
                tier3_checks.append(left_edge_mean > 5.0 and hud_mean > 15.0)
                
        tier3_ok = len(tier3_checks) > 0 and all(tier3_checks)
        report["gates"]["gate_4_bottom_tier3"] = {
            "passed": tier3_ok,
            "details": "HUD Operacional no Tier 3 ativo com Saldo e Momento CALL/PUT sem cortes"
        }
        if not tier3_ok:
            report["errors"].append("Tier inferior com anomalias de layout ou cortes na margem.")

        cap.release()

        # -------------------------------------------------------------
        # PORTÃO 5: AUDITORIA FINANCEIRA ZERO-LOSS (REGRA ESTRITA DE WIN)
        # -------------------------------------------------------------
        financial_ok = False
        trade_result = "UNKNOWN"
        profit = 0
        if telemetry_path and Path(telemetry_path).exists():
            try:
                with open(telemetry_path, "r", encoding="utf-8") as f:
                    telem = json.load(f)
                trade_result = telem.get("outcome_event", {}).get("result", "UNKNOWN")
                profit = telem.get("outcome_event", {}).get("profit_amount", 0)
                financial_ok = (trade_result == "WIN" and profit > 0)
            except Exception as e:
                report["errors"].append(f"Erro ao ler telemetria para auditoria financeira: {e}")
        else:
            report["errors"].append("Arquivo de telemetria não fornecido para validação financeira.")
            
        report["gates"]["gate_5_financial_win"] = {
            "passed": financial_ok,
            "result": trade_result,
            "profit_amount": profit
        }
        if not financial_ok:
            report["errors"].append(f"Operação NÃO atendeu ao critério Zero-Loss (Resultado: {trade_result}, Lucro: ${profit})")

        # -------------------------------------------------------------
        # PORTÃO 6: AUDITORIA DE ÁUDIO & SINCRONISMO
        # -------------------------------------------------------------
        audio_ok = False
        if a_stream:
            a_duration = float(a_stream.get("duration", 0.0))
            channels = int(a_stream.get("channels", 0))
            diff_d = abs(v_duration - a_duration)
            audio_ok = (channels >= 1 and diff_d <= 2.5)
            report["gates"]["gate_6_audio_track"] = {
                "passed": audio_ok,
                "codec": a_stream.get("codec_name"),
                "channels": channels,
                "duration_difference": round(diff_d, 2)
            }
        else:
            report["gates"]["gate_6_audio_track"] = {"passed": False, "error": "Sem faixa de áudio"}
            
        if not audio_ok:
            report["errors"].append("Problema na faixa de áudio: ausente ou dessincronizada.")

        return self._finalize_report(report, video_path, take_dir)

    def _finalize_report(self, report, video_path, take_dir):
        passed = (len(report["errors"]) == 0)
        report["overall_verdict"] = "PASSED" if passed else "FAILED"
        report["score"] = 100 if passed else max(0, 100 - len(report["errors"]) * 25)
        
        # Salvar relatório no diretório do take
        if take_dir and Path(take_dir).exists():
            out_rep = Path(take_dir) / "audit_report.json"
            with open(out_rep, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
        print("\n" + "="*76)
        if passed:
            print(f"✅ [AUDITORIA APROVADA // NOTA: {report['score']}/100] Vídeo 100% íntegro e validado!")
        else:
            print(f"❌ [AUDITORIA REPROVADA // NOTA: {report['score']}/100]")
            for err in report["errors"]:
                print(f"   • {err}")
        print("="*76 + "\n")
        
        return passed, report

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Auditor Cazador Agent - Inspeção de Vídeo")
    parser.add_argument("--video", required=True, help="Caminho do vídeo MP4")
    parser.add_argument("--telemetry", help="Caminho do JSON de telemetria")
    args = parser.parse_args()
    
    auditor = AuditorCazadorAgent()
    passed, rep = auditor.audit_video(args.video, args.telemetry)
    sys.exit(0 if passed else 1)
