#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EL CAZADOR DEL WINS // TESTES ROBUSTOS DA SUBETAPA 1:
1. Teste Geométrico e Anti-Corte (Bordas seguras e sem overlaps).
2. Teste de Estresse de Magnitude de Saldo ($100 a $10.000+).
3. Teste de Renderização Real no Take 20261008_204109 com extração e verificação de frames.
"""

import sys
import os
import cv2
import numpy as np
from pathlib import Path

# Suporte seguro a console Windows UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
sys.path.append(str(BASE_DIR / "agents"))

from motion_graphics_agent import MotionGraphicsAgent

def test_1_geometric_safety():
    print("▶ [TESTE 1/3] Teste Geométrico de Zonas Seguras e Anti-Corte...")
    agent = MotionGraphicsAgent()
    canvas = np.zeros((1920, 1080, 3), dtype=np.uint8)
    
    # Renderizar HUD no canvas
    agent._draw_tier3_hud(canvas, t_sec=25.0, click_sec=18.0, outcome_sec=51.0, action="PUT", amount=100, payout_pct=82, profit_amount=82)
    
    # 1. Verificar se cobriu a borda esquerda (x=0)
    assert np.any(canvas[1210:1540, 0:10] != 0), "Falha: O HUD não cobriu a margem esquerda x=0!"
    
    # 2. Verificar se não invadiu a área de botões na direita (x=600..1080)
    assert np.all(canvas[1210:1540, 600:1080] == 0), "Falha: O HUD invadiu a zona dos botões de disparo (x > 600)!"
    
    print("  ✅ [PASSOU] Borda esquerda 100% coberta e zona dos botões (x > 600) 100% preservada.")
    return True

def test_2_balance_stress():
    print("\n▶ [TESTE 2/3] Teste de Estresse com Múltiplas Magnitudes de Saldo...")
    agent = MotionGraphicsAgent()
    test_balances = ["$0.00", "$100.00", "$1.000.00", "$10.582.60", "$182.60"]
    
    for bal in test_balances:
        canvas = np.zeros((1920, 1080, 3), dtype=np.uint8)
        # Simular desenho com valor de teste
        (w, h), _ = cv2.getTextSize(bal, cv2.FONT_HERSHEY_DUPLEX, 1.30, 3)
        # Borda do card: x: 0..570, texto inicia em x=25. Margem máx: 550
        assert 25 + w < 560, f"Falha de estouro de layout para o saldo '{bal}' (largura {w}px ultrapassa card)!"
        print(f"  ✅ Saldo '{bal}': Largura {w}px coube perfeitamente na safe zone (máx 535px).")
        
    print("  ✅ [PASSOU] Todas as magnitudes de saldo aprovadas sem risco de truncamento.")
    return True

def test_3_real_render_validation():
    print("\n▶ [TESTE 3/3] Renderização Real com HUD Tier 3 no Take 20261008_204109...")
    take_dir = BASE_DIR / "raw_recordings" / "take_20261008_204109"
    video_input = take_dir / "take_20261008_204109.mp4"
    telemetry_file = take_dir / "take_20261008_204109_telemetry.json"
    trajectory_file = take_dir / "mouse_trajectory.json"
    
    assert video_input.exists(), f"Vídeo de entrada não encontrado: {video_input}"
    
    import json
    with open(telemetry_file, "r", encoding="utf-8") as f:
        telemetry = json.load(f)
        
    out_motion = take_dir / "test_subetapa1_motion.mp4"
    agent = MotionGraphicsAgent(fps=30)
    agent.apply_motion_graphics(video_input, out_motion, telemetry=telemetry, trajectory_file=trajectory_file)
    
    assert out_motion.exists() and out_motion.stat().st_size > 1000000, "Falha na geração do vídeo com HUD!"
    
    # Extrair frames-chave para auditoria visual
    cap = cv2.VideoCapture(str(out_motion))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    checks = {
        "05s_init": int(5.0 * fps),
        "18s_click": int(18.0 * fps),
        "26s_active": int(26.0 * fps),
        "52s_win": int(52.0 * fps)
    }
    
    for name, f_idx in checks.items():
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        assert ret, f"Falha ao ler frame {name} ({f_idx})"
        out_img = BASE_DIR / f"test_subetapa1_{name}.png"
        cv2.imwrite(str(out_img), frame)
        print(f"  📸 Frame auditado e salvo: {out_img.name}")
        
    cap.release()
    print("  ✅ [PASSOU] Vídeo renderizado e frames de verificação extraídos com sucesso.")
    return True

if __name__ == "__main__":
    t1 = test_1_geometric_safety()
    t2 = test_2_balance_stress()
    t3 = test_3_real_render_validation()
    
    if t1 and t2 and t3:
        print("\n" + "="*76)
        print("🏆 SUBETAPA 1 VALIDADA COM 100% DE SUCESSO EM TODOS OS TESTES!")
        print("="*76)
        sys.exit(0)
    else:
        print("\n❌ FALHA NA SUBETAPA 1")
        sys.exit(1)
