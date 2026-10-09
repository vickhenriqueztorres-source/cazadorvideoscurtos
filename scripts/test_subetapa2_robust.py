#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EL CAZADOR DEL WINS // TESTES ROBUSTOS DA SUBETAPA 2:
1. Teste Positivo: Auditoria em vídeo real perfeito -> DEVE APROVAR (PASSED).
2. Teste de Caos 1: Vídeo com Cabeçalho Corrompido -> DEVE REPROVAR (Gate 3).
3. Teste de Caos 2: Telemetria com LOSS Financeiro -> DEVE REPROVAR (Gate 5).
4. Teste de Caos 3: Vídeo sem Faixa de Áudio -> DEVE REPROVAR (Gate 6).
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path

# Suporte seguro a console Windows UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
sys.path.append(str(BASE_DIR / "agents"))

from auditor_cazador_agent import AuditorCazadorAgent

def test_1_positive_audit():
    print("▶ [TESTE 1/4] Auditoria Positiva do Vídeo Master Real...")
    video_path = BASE_DIR / "output_shorts" / "take_20261008_204109_final.mp4"
    telemetry_path = BASE_DIR / "raw_recordings" / "take_20261008_204109" / "take_20261008_204109_telemetry.json"
    
    assert video_path.exists(), f"Vídeo não encontrado: {video_path}"
    assert telemetry_path.exists(), f"Telemetria não encontrada: {telemetry_path}"
    
    auditor = AuditorCazadorAgent()
    passed, report = auditor.audit_video(video_path, telemetry_path)
    
    assert passed, f"Falha inesperada no teste positivo: {report['errors']}"
    assert report["score"] == 100, f"Nota deveria ser 100, mas foi {report['score']}"
    print("  ✅ [PASSOU] Vídeo real aprovado com louvor (Nota 100/100).")
    return True

def test_2_chaos_corrupted_header():
    print("\n▶ [TESTE 2/4] Teste de Caos 1: Injeção de Cabeçalho Corrompido/Preto...")
    import cv2, numpy as np
    
    # Criar um vídeo sintético onde o cabeçalho superior (0..160) é propositalmente preto
    tmp_video = BASE_DIR / "scratch_chaos_header.mp4"
    cap = cv2.VideoCapture(str(BASE_DIR / "output_shorts" / "take_20261008_204109_final.mp4"))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(tmp_video), fourcc, 30.0, (1080, 1920))
    
    # Gravar 100 frames com cabeçalho zerado
    for _ in range(100):
        ret, frame = cap.read()
        if not ret: break
        frame[0:160, :] = 0 # Corromper o cabeçalho
        out.write(frame)
        
    cap.release()
    out.release()
    
    auditor = AuditorCazadorAgent()
    telemetry_path = BASE_DIR / "raw_recordings" / "take_20261008_204109" / "take_20261008_204109_telemetry.json"
    passed, report = auditor.audit_video(tmp_video, telemetry_path)
    
    if tmp_video.exists():
        tmp_video.unlink()
        
    assert not passed, "Falha: O auditor DEVERIA ter reprovado o cabeçalho corrompido!"
    assert not report["gates"]["gate_3_header_tier1"]["passed"], "Gate 3 deveria ter falhado!"
    print("  ✅ [PASSOU] Cabeçalho corrompido detectado e reprovado com sucesso!")
    return True

def test_3_chaos_loss_telemetry():
    print("\n▶ [TESTE 3/4] Teste de Caos 2: Injeção de Operação Perdedora (LOSS)...")
    video_path = BASE_DIR / "output_shorts" / "take_20261008_204109_final.mp4"
    fake_telemetry = BASE_DIR / "scratch_fake_loss_telemetry.json"
    
    with open(fake_telemetry, "w", encoding="utf-8") as f:
        json.dump({
            "outcome_event": {
                "result": "LOSS",
                "profit_amount": -100
            }
        }, f)
        
    auditor = AuditorCazadorAgent()
    passed, report = auditor.audit_video(video_path, fake_telemetry)
    
    if fake_telemetry.exists():
        fake_telemetry.unlink()
        
    assert not passed, "Falha: O auditor DEVERIA ter reprovado a operação com LOSS!"
    assert not report["gates"]["gate_5_financial_win"]["passed"], "Gate 5 deveria ter falhado!"
    print("  ✅ [PASSOU] Tentativa de publicar LOSS bloqueada sumariamente pelo auditor!")
    return True

def test_4_chaos_missing_audio():
    print("\n▶ [TESTE 4/4] Teste de Caos 3: Injeção de Vídeo sem Faixa de Áudio...")
    tmp_no_audio = BASE_DIR / "scratch_no_audio.mp4"
    
    # Criar cópia do vídeo removendo o áudio via ffmpeg
    cmd = [
        "ffmpeg", "-y", "-i", str(BASE_DIR / "output_shorts" / "take_20261008_204109_final.mp4"),
        "-t", "5", "-an", "-c:v", "copy", str(tmp_no_audio)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    auditor = AuditorCazadorAgent()
    telemetry_path = BASE_DIR / "raw_recordings" / "take_20261008_204109" / "take_20261008_204109_telemetry.json"
    passed, report = auditor.audit_video(tmp_no_audio, telemetry_path)
    
    if tmp_no_audio.exists():
        tmp_no_audio.unlink()
        
    assert not passed, "Falha: O auditor DEVERIA ter reprovado o vídeo sem áudio!"
    assert not report["gates"]["gate_6_audio_track"]["passed"], "Gate 6 deveria ter falhado!"
    print("  ✅ [PASSOU] Vídeo mudo bloqueado sumariamente pelo auditor!")
    return True

if __name__ == "__main__":
    t1 = test_1_positive_audit()
    t2 = test_2_chaos_corrupted_header()
    t3 = test_3_chaos_loss_telemetry()
    t4 = test_4_chaos_missing_audio()
    
    if t1 and t2 and t3 and t4:
        print("\n" + "="*76)
        print("🏆 SUBETAPA 2 VALIDADA COM 100% DE SUCESSO EM TODOS OS TESTES (INCLUINDO CAOS)!")
        print("="*76)
        sys.exit(0)
    else:
        print("\n❌ FALHA NA SUBETAPA 2")
        sys.exit(1)
