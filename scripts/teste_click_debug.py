#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário de Teste de Movimentação, Hover e Clique Seguro - IQ Option
Testa a precisão milimétrica dos movimentos e cliques sem colocar ordens financeiras reais.
"""

import sys
import json
import time
import argparse
from pathlib import Path
import pyautogui

from desktop_util import attach_to_default_desktop

# UTF-8 stdout
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.15

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
CONFIG_FILE = BASE_DIR / "config" / "iqoption_coords.json"

def run_hover_test():
    print("=== TESTE DE HOVER E MIRA HUMANA (AGENT-CARTOGRAPHER) ===")
    attach_to_default_desktop()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    elements = data.get("elements_1080p", {})
    
    print("Iniciando varredura suave de mira...")
    time.sleep(0.5)
    
    log_results = []
    for name, item in elements.items():
        x, y = item["x"], item["y"]
        t_start = time.perf_counter()
        
        # Movimentação suave com easing idêntica à que o CazadorRecorderAgent usa
        pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeInOutQuad)
        actual_pos = pyautogui.position()
        delta_x = abs(actual_pos.x - x)
        delta_y = abs(actual_pos.y - y)
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        
        status = "EXATO" if delta_x == 0 and delta_y == 0 else f"DESVIO({delta_x},{delta_y})"
        print(f"  [MIRA] {name:25s} -> Target: ({x:4d}, {y:4d}) | Mouse: ({actual_pos.x:4d}, {actual_pos.y:4d}) | {status} ({elapsed_ms:.1f}ms)")
        log_results.append({"name": name, "target": (x, y), "actual": (actual_pos.x, actual_pos.y), "status": status})
        time.sleep(0.1)
        
    print(f"\n[OK] Varredura de hover concluída. Todos os {len(log_results)} pontos testados!")
    return log_results

def run_safe_click_test():
    print("=== TESTE DE CLIQUE SEGURO (SAFE-CLICK) ===")
    attach_to_default_desktop()
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    elements = data.get("elements_1080p", {})
    
    # Testar foco e clique neutro em 'centro_grafico'
    target = elements.get("centro_grafico", {"x": 960, "y": 540})
    print(f"Testando foco e clique neutro em 'centro_grafico': ({target['x']}, {target['y']})")
    
    pyautogui.moveTo(target["x"], target["y"], duration=0.3, tween=pyautogui.easeInOutQuad)
    t0 = time.perf_counter()
    pyautogui.click()
    click_latency_ms = (time.perf_counter() - t0) * 1000
    
    print(f"[OK] Clique neutro executado com sucesso! Latência do clique: {click_latency_ms:.2f}ms")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de Hover e Clique Debug")
    parser.add_argument("--mode", choices=["hover", "safe-click", "all"], default="all")
    args = parser.parse_args()
    
    if args.mode in ["hover", "all"]:
        run_hover_test()
    if args.mode in ["safe-click", "all"]:
        run_safe_click_test()
