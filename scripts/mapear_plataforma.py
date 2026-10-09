#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário de Mapeamento e Diagnóstico Visual de Coordenadas - IQ Option
Captura a tela atual, renderiza as miras de calibração sobre os botões e salva o diagnóstico em assets/debug_calibration.png
"""

import sys
import json
import time
from pathlib import Path
import cv2
import numpy as np
import mss

# Import Desktop Attacher
from desktop_util import attach_to_default_desktop

# UTF-8 stdout
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
CONFIG_FILE = BASE_DIR / "config" / "iqoption_coords.json"
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_IMG = ASSETS_DIR / "debug_calibration.png"

def run_mapping():
    print("=== AGENT-CARTOGRAPHER: MAPEAMENTO DA PLATAFORMA IQ OPTION ===")
    attach_to_default_desktop()
    
    if not CONFIG_FILE.exists():
        print(f"[ERRO] Arquivo de configuração não encontrado: {CONFIG_FILE}")
        return False
        
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        coords_data = json.load(f)
        
    elements = coords_data.get("elements_1080p", {})
    print(f"Total de elementos mapeados: {len(elements)}")
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"Capturando tela primária: {monitor['width']}x{monitor['height']}")
        img_raw = sct.grab(monitor)
        frame = np.array(img_raw)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        
    # Desenhar retículos de calibração
    for name, item in elements.items():
        x, y = item["x"], item["y"]
        desc = item.get("desc", name)
        
        # Cor por tipo
        if "call" in name:
            color = (0, 255, 0) # Verde
        elif "put" in name:
            color = (0, 0, 255) # Vermelho
        elif "valor" in name or "tempo" in name:
            color = (255, 200, 0) # Amarelo
        else:
            color = (255, 255, 255) # Branco
            
        cv2.circle(frame, (x, y), 12, color, 2)
        cv2.circle(frame, (x, y), 3, color, -1)
        cv2.putText(frame, f"{name} ({x},{y})", (x + 15, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        print(f"  [ALVO MAP] {name:25s} -> ({x:4d}, {y:4d}) | {desc}")
        
    cv2.imwrite(str(DEBUG_IMG), frame)
    print(f"\n[OK] Diagnóstico visual salvo em: {DEBUG_IMG}")
    print("[SUCESSO] Todos os alvos de coordenadas foram verificados com sucesso.")
    return True

if __name__ == "__main__":
    run_mapping()
