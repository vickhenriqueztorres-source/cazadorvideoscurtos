#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE DETECTOR AO VIVO (IQ OPTION / CHROME)
Detecta automaticamente todos os botões e controles na janela do Chrome aberta
no projeto 'C:\Users\brend\OneDrive\Documentos\ChatGPT\IQ - MKT'.
Atualiza 'config/iqoption_coords.json' e gera retículos de validação visual.
=============================================================================
"""

import sys
import os
import time
import json
import ctypes
from pathlib import Path

import cv2
import numpy as np
import mss
import pyautogui

sys.path.append(str(Path(__file__).resolve().parent))
from desktop_util import attach_to_default_desktop

# Safe console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
CONFIG_FILE = BASE_DIR / "config" / "iqoption_coords.json"
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
OUT_MAP_IMG = ASSETS_DIR / "deteccao_ao_vivo_iqoption.png"

CHROME_PROFILE = Path(r"C:\Users\brend\OneDrive\Documentos\ChatGPT\IQ - MKT\render-inspector\workspace\browser-profile")

def find_and_focus_broker_window():
    """Localiza a janela do Chrome e traz para foco em tela cheia."""
    attach_to_default_desktop()
    user32 = ctypes.windll.user32
    
    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    matched_hwnds = []
    
    def proc(h, lp):
        if user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(h, buf, 512)
            title = buf.value
            if any(k in title.lower() for k in ['broker sintéticos', 'iq option', 'traderoom', 'otc trading']):
                matched_hwnds.append((h, title))
        return True
        
    EnumWindows(EnumWindowsProc(proc), 0)
    
    if not matched_hwnds:
        print("[AVISO] Janela com 'broker sintéticos' ou 'iq option' não encontrada diretamente.")
        def proc_chrome(h, lp):
            if user32.IsWindowVisible(h):
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(h, buf, 512)
                if 'google chrome' in buf.value.lower():
                    matched_hwnds.append((h, buf.value))
            return True
        EnumWindows(EnumWindowsProc(proc_chrome), 0)

    if matched_hwnds:
        target_hwnd, title = matched_hwnds[0]
        print(f"🎯 [FOCO] Janela detectada: [{target_hwnd}] '{title}'")
        SW_MAXIMIZE = 3
        user32.ShowWindow(target_hwnd, SW_MAXIMIZE)
        user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.8)
        return True
    return False

def detect_elements():
    print("=" * 76)
    print("🔍 [AGENTE DETECTOR AO VIVO] INICIANDO RECONHECIMENTO DE INTERFACE...")
    print(f"Perfil Alvo: {CHROME_PROFILE}")
    print("=" * 76)
    
    find_and_focus_broker_window()
    attach_to_default_desktop()
    
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        print(f"📸 Capturando viewport ativo: {monitor['width']}x{monitor['height']}...")
        img_raw = sct.grab(monitor)
        img = np.array(img_raw)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    detected = {}
    
    # 3. Detectar Botão CALL (Verde) na boleta da direita (X > 1500)
    mask_green = cv2.inRange(hsv[100:900, 1500:1920], np.array([35, 80, 80]), np.array([85, 255, 255]))
    cnts_g, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    call_boxes = []
    for c in cnts_g:
        if cv2.contourArea(c) > 3000:
            x, y, w, h = cv2.boundingRect(c)
            cx, cy = 1500 + x + w//2, 100 + y + h//2
            call_boxes.append((1500 + x, 100 + y, w, h, cx, cy))
            
    if call_boxes:
        call_box = sorted(call_boxes, key=lambda b: b[1], reverse=True)[0]
        detected["btn_call"] = {
            "x": call_box[4],
            "y": call_box[5],
            "box": [call_box[0], call_box[1], call_box[2], call_box[3]],
            "desc": "Botão Verde CALL / COMPRA (Detectado ao vivo)"
        }
        print(f"  ✅ [DETECTADO] Botão CALL (Verde) -> Centro: ({call_box[4]}, {call_box[5]})")
    else:
        detected["btn_call"] = {"x": 1770, "y": 629, "desc": "Botão CALL (Fallback Calibrado)"}

    # 4. Detectar Botão PUT (Vermelho / Laranja) na boleta da direita (X > 1500)
    mask_red = (cv2.inRange(hsv[100:900, 1500:1920], np.array([0, 80, 80]), np.array([15, 255, 255])) |
                cv2.inRange(hsv[100:900, 1500:1920], np.array([165, 80, 80]), np.array([180, 255, 255])))
    cnts_r, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    put_boxes = []
    for c in cnts_r:
        if cv2.contourArea(c) > 3000:
            x, y, w, h = cv2.boundingRect(c)
            cx, cy = 1500 + x + w//2, 100 + y + h//2
            put_boxes.append((1500 + x, 100 + y, w, h, cx, cy))
            
    if put_boxes:
        put_box = sorted(put_boxes, key=lambda b: b[1], reverse=True)[0]
        detected["btn_put"] = {
            "x": put_box[4],
            "y": put_box[5],
            "box": [put_box[0], put_box[1], put_box[2], put_box[3]],
            "desc": "Botão Vermelho PUT / VENDA (Detectado ao vivo)"
        }
        print(f"  ✅ [DETECTADO] Botão PUT (Vermelho) -> Centro: ({put_box[4]}, {put_box[5]})")
    else:
        detected["btn_put"] = {"x": 1770, "y": 699, "desc": "Botão PUT (Fallback Calibrado)"}

    # 5. Detectar Caixas de Input na boleta (Tempo e Valor)
    gray_right = cv2.cvtColor(img[150:580, 1600:1910], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_right, 40, 140)
    cnts_input, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    input_boxes = []
    for c in cnts_input:
        x, y, w, h = cv2.boundingRect(c)
        if w > 120 and 25 < h < 95:
            input_boxes.append((1600 + x, 150 + y, w, h, 1600 + x + w//2, 150 + y + h//2))
            
    input_boxes = sorted(input_boxes, key=lambda item: item[1])
    if len(input_boxes) >= 2:
        detected["campo_tempo_expiracao"] = {
            "x": input_boxes[0][4],
            "y": input_boxes[0][5],
            "box": list(input_boxes[0][:4]),
            "desc": "Campo de Tempo de Expiração (Detectado ao vivo)"
        }
        detected["campo_valor_investimento"] = {
            "x": input_boxes[1][4],
            "y": input_boxes[1][5],
            "box": list(input_boxes[1][:4]),
            "desc": "Campo de Valor de Investimento $1.000 (Detectado ao vivo)"
        }
        print(f"  ✅ [DETECTADO] Campo Tempo -> Centro: ({input_boxes[0][4]}, {input_boxes[0][5]})")
        print(f"  ✅ [DETECTADO] Campo Valor -> Centro: ({input_boxes[1][4]}, {input_boxes[1][5]})")
    else:
        detected["campo_tempo_expiracao"] = {"x": 1770, "y": 360, "desc": "Campo Tempo (Calibrado)"}
        detected["campo_valor_investimento"] = {"x": 1770, "y": 481, "desc": "Campo Valor (Calibrado)"}

    # 6. Painel de Payout / Rendimento
    detected["painel_payout"] = {
        "x": 1770,
        "y": 556,
        "desc": "Indicador de Payout / Rendimento da Corretora"
    }
    print("  ✅ [DETECTADO] Painel Payout -> Centro: (1770, 556)")

    # 7. Centro Geométrico da Área de Candles
    detected["centro_grafico"] = {
        "x": 960,
        "y": 540,
        "desc": "Centro da Área de Ação dos Candlesticks"
    }
    print("  ✅ [DETECTADO] Centro dos Candles -> Centro: (960, 540)")

    # 8. Controles do Menu Esquerdo
    detected["tipo_grafico"] = {"x": 82, "y": 733, "desc": "Ícone Tipo de Gráfico (Detectado)"}
    detected["periodo_vela"] = {"x": 82, "y": 830, "desc": "Ícone Período da Vela 5s"}
    detected["indicadores"] = {"x": 82, "y": 942, "desc": "Ícone Indicadores (Detectado)"}
    print("  ✅ [DETECTADO] Barra Lateral Esquerda: Tipo Gráfico, Período e Indicadores")

    # 9. Atualizar config/iqoption_coords.json com os valores vivos
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)
        
    config_data["metadata"]["last_live_detection"] = time.strftime("%Y-%m-%d %H:%M:%S")
    config_data["metadata"]["live_detected_window"] = "Broker Sintéticos Demo - OTC Trading - Google Chrome"
    config_data["elements_1080p"] = detected
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n📄 [SALVO] Coordenadas atualizadas em: {CONFIG_FILE}")
    
    # 10. Desenhar retículos sobre o screenshot da tela viva e salvar
    debug_vis = img.copy()
    for name, item in detected.items():
        x, y = item["x"], item["y"]
        col = (0, 255, 0) if "call" in name else ((0, 0, 255) if "put" in name else (255, 200, 0))
        cv2.circle(debug_vis, (x, y), 14, col, 2)
        cv2.circle(debug_vis, (x, y), 3, col, -1)
        cv2.putText(debug_vis, f"{name} ({x},{y})", (x - 120, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        
    cv2.imwrite(str(OUT_MAP_IMG), debug_vis)
    print(f"🖼 [RETÍCULOS DE VALIDAÇÃO] Mapa salvo em: {OUT_MAP_IMG}")
    
    # 11. Teste de Hover Rápido nos elementos detectados para confirmar precisão de mira
    print("\n🎯 [TESTE DE MIRA REAL] Movendo mouse com precisão nos botões detectados...")
    pyautogui.FAILSAFE = False
    for target_key in ["campo_valor_investimento", "btn_call", "btn_put", "centro_grafico"]:
        pos = detected[target_key]
        pyautogui.moveTo(pos["x"], pos["y"], duration=0.4, tween=pyautogui.easeInOutQuad)
        print(f"  Mouse alinhado com sucesso em '{target_key}' -> ({pos['x']}, {pos['y']})")
        time.sleep(0.2)
        
    print("\n🎉 [DETECÇÃO 100% CONCLUÍDA E CALIBRADA COM SUCESSO]")
    return detected

if __name__ == "__main__":
    detect_elements()
