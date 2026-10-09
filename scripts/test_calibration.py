#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário seguro para testar calibração dos pontos da IQ Option sem disparar ordens.
"""
import sys
import time
import json
from pathlib import Path
import pyautogui

CONFIG_FILE = Path("D:/cazador - videos curtos/config/iqoption_coords.json").resolve()

def test_coords():
    if not CONFIG_FILE.exists():
        print(f"Erro: Arquivo {CONFIG_FILE} não encontrado.")
        return
        
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    elements = data.get("elements", {})
    print("=== TESTE DE MIRA DE COORDENADAS (IQ OPTION) ===")
    print("O mouse moverá suavemente sobre cada coordenada calibrada.")
    print("Pressione Ctrl+C a qualquer momento para cancelar.\n")
    time.sleep(2)
    
    for name, item in elements.items():
        x, y = item["x"], item["y"]
        desc = item.get("desc", "")
        print(f"Mirando em: {name} ({x}, {y}) - {desc}")
        pyautogui.moveTo(x, y, duration=0.8, tween=pyautogui.easeInOutQuad)
        time.sleep(0.5)
        
    print("\n[OK] Teste de coordenadas finalizado com sucesso!")

if __name__ == "__main__":
    test_coords()
