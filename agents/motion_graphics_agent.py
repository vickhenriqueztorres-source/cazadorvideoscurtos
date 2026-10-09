#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: MotionGraphicsAgent
Renderizador de Animações, Zooms Dinâmicos, Cursor do Mouse e Motion Callouts:
- Projeção geométrica do Mouse da tela 1920x1080 para o formato vertical 9:16
- Renderização de cursor de alta definição com halo de foco
- Sistema Cinematográfico de ZOOMS DINÂMICOS nas fases-chave:
  * Gancho Inicial (punch de impacto nas velas)
  * Macro-Zoom no Pavio de Rejeição (1.30x cirúrgico)
  * Tensão no Botão HIGHER no Segundo 31 (1.25x macro)
  * Punch Shockwave no momento exato do clique mecânico (1.28x)
  * Tensão da Vela ao vivo com Tasa Blindada (1.14x)
  * Victory Punch Dopamina no WIN (1.20x)
  * Cabeçalho de Saldo (0..160px) SEMPRE 100% fixo, nítido e sem cortes
- Efeito de onda de choque no clique do mouse (Click Ripple)
- Marcações cirúrgicas nas velas com acompanhamento do zoom
=============================================================================
"""

import cv2
import numpy as np
import json
import time
import subprocess
from pathlib import Path

def map_screen_coords_to_vertical(mx, my):
    """
    Projeta coordenadas da tela nativa 1920x1080 para o layout vertical 1080x1920:
    - Tier 1 (Cabeçalho): 0 <= y < 160 (fixo, logo IQ e saldo inalterados)
    - Tier 2 (Candlesticks): 580 <= x <= 1280, 220 <= y <= 760 -> Y: 160 a 1180 (altura 1020)
    - Tier 3 (Painel Gatilho): 1312 <= x <= 1920, 150 <= y <= 710 -> Y: 1180 a 1920 (altura 740)
    """
    if mx is None or my is None:
        return None, None, None
        
    if mx < 1300:
        clamped_mx = max(580, min(1280, mx))
        clamped_my = max(200, min(760, my))
        vx = int((clamped_mx - 580) * (1080.0 / 700.0))
        vy = int(160 + (clamped_my - 220) * (1020.0 / 540.0))
        return max(0, min(1079, vx)), max(160, min(1179, vy)), "candlesticks"
    else:
        clamped_mx = max(1312, min(1920, mx))
        clamped_my = max(140, min(710, my))
        vx = int((clamped_mx - 1312) * (1080.0 / 608.0))
        vy = int(1180 + (clamped_my - 150) * (740.0 / 560.0))
        return max(0, min(1079, vx)), max(1180, min(1919, vy)), "trigger_panel"

def apply_smooth_zoom(region, zoom_factor, cx_rel=0.5, cy_rel=0.5):
    """Aplica zoom suave em uma região sem alterar suas dimensões finais."""
    if zoom_factor <= 1.001:
        return region, 0, 0, region.shape[1], region.shape[0]
    h, w = region.shape[:2]
    crop_w = int(w / zoom_factor)
    crop_h = int(h / zoom_factor)
    center_px_x = int(w * cx_rel)
    center_px_y = int(h * cy_rel)
    x1 = max(0, min(w - crop_w, center_px_x - crop_w // 2))
    y1 = max(0, min(h - crop_h, center_px_y - crop_h // 2))
    x2 = x1 + crop_w
    y2 = y1 + crop_h
    cropped = region[y1:y2, x1:x2]
    zoomed = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    return zoomed, x1, y1, crop_w, crop_h

def transform_point_zoom(px, py, w, h, x1, y1, crop_w, crop_h):
    """Mapeia um ponto (px, py) para as coordenadas da imagem ampliada."""
    if crop_w == w and crop_h == h:
        return px, py
    rx = px - x1
    ry = py - y1
    new_px = int(rx * (w / crop_w))
    new_py = int(ry * (h / crop_h))
    return new_px, new_py

def smooth_step(edge0, edge1, x):
    """Interpolação Hermite suave para transições cinematográficas de câmera."""
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)

def get_dynamic_zooms(t_sec, click_sec, outcome_sec, cx_wick_rel=0.73, cy_wick_rel=0.60, cx_btn_rel=0.85, cy_btn_rel=0.45):
    """
    Calcula curvas de zoom para dar máximo dinamismo e retenção:
    - Retorna: (zoom_mid, cx_mid, cy_mid, zoom_bot, cx_bot, cy_bot)
    """
    z_mid, cx_m, cy_m = 1.0, 0.5, 0.5
    z_bot, cx_b, cy_b = 1.0, cx_btn_rel, cy_btn_rel
    
    # 1. Gancho de Abertura (0.5s a 3.2s) - Punch nas velas
    if 0.5 <= t_sec < 1.5:
        p = smooth_step(0.5, 1.5, t_sec)
        z_mid = 1.0 + 0.16 * p
    elif 1.5 <= t_sec < 2.5:
        z_mid = 1.16
    elif 2.5 <= t_sec < 3.2:
        p = smooth_step(2.5, 3.2, t_sec)
        z_mid = 1.16 - 0.16 * p
        
    # 2. Explicação do Pavio de Rejeição (8.5s a 13.8s) - Macro zoom 1.28x
    elif 8.5 <= t_sec < 9.5:
        p = smooth_step(8.5, 9.5, t_sec)
        z_mid = 1.0 + 0.28 * p
        cx_m, cy_m = cx_wick_rel, cy_wick_rel
    elif 9.5 <= t_sec < 12.8:
        z_mid = 1.28
        cx_m, cy_m = cx_wick_rel, cy_wick_rel
    elif 12.8 <= t_sec < 13.8:
        p = smooth_step(12.8, 13.8, t_sec)
        z_mid = 1.28 - 0.28 * p
        cx_m, cy_m = cx_wick_rel, cy_wick_rel

    # 3. Tensão no Gatilho / Segundo 31 (14.5s até o clique)
    if 14.5 <= t_sec < (click_sec - 0.4):
        p = smooth_step(14.5, click_sec - 0.4, t_sec)
        z_bot = 1.0 + 0.25 * p
    elif (click_sec - 0.4) <= t_sec <= (click_sec + 0.3):
        # Punch do clique
        z_bot = 1.28
    elif (click_sec + 0.3) < t_sec < (click_sec + 1.2):
        p = smooth_step(click_sec + 0.3, click_sec + 1.2, t_sec)
        z_bot = 1.28 - 0.28 * p

    # 4. Tensão da Vela ao Vivo (24.0s até outcome_sec - 1.5s)
    if 24.0 <= t_sec < 25.5:
        p = smooth_step(24.0, 25.5, t_sec)
        z_mid = 1.0 + 0.15 * p
        cx_m, cy_m = 0.65, 0.45
    elif 25.5 <= t_sec < (outcome_sec - 1.5):
        z_mid = 1.15
        cx_m, cy_m = 0.65, 0.45
    elif (outcome_sec - 1.5) <= t_sec < outcome_sec:
        p = smooth_step(outcome_sec - 1.5, outcome_sec, t_sec)
        z_mid = 1.15 - 0.15 * p
        cx_m, cy_m = 0.65, 0.45

    # 5. Dopamina da Vitória / WIN (outcome_sec até o final)
    if outcome_sec <= t_sec < (outcome_sec + 0.8):
        p = smooth_step(outcome_sec, outcome_sec + 0.8, t_sec)
        z_mid = 1.0 + 0.22 * p
        cx_m, cy_m = 0.5, 0.5
    elif (outcome_sec + 0.8) <= t_sec:
        z_mid = 1.22
        cx_m, cy_m = 0.5, 0.5

    return z_mid, cx_m, cy_m, z_bot, cx_b, cy_b

def draw_cursor_pointer(frame, vx, vy, highlight=True):
    """Desenha um ponteiro de mouse limpo e visível com halo de destaque."""
    h_frame, w_frame = frame.shape[:2]
    if vx is None or vy is None or vx < 0 or vx >= w_frame or vy < 0 or vy >= h_frame:
        return
        
    # 1. Halo de foco suave (amarelo/ciano semitransparente)
    if highlight:
        overlay = frame.copy()
        cv2.circle(overlay, (vx, vy), 26, (0, 235, 255), -1)
        cv2.addWeighted(overlay, 0.28, frame, 0.72, 0, frame)
        cv2.circle(frame, (vx, vy), 26, (0, 200, 255), 1, cv2.LINE_AA)

    # 2. Polígono do ponteiro do mouse clássico
    pts = np.array([
        [vx, vy],
        [vx, vy + 22],
        [vx + 6, vy + 17],
        [vx + 11, vy + 27],
        [vx + 16, vy + 25],
        [vx + 11, vy + 15],
        [vx + 18, vy + 15]
    ], dtype=np.int32)
    
    # Sombra
    shadow_pts = pts + 2
    cv2.fillPoly(frame, [shadow_pts], color=(10, 10, 15), lineType=cv2.LINE_AA)
    # Contorno preto
    cv2.polylines(frame, [pts], isClosed=True, color=(0, 0, 0), thickness=3, lineType=cv2.LINE_AA)
    # Preenchimento branco
    cv2.fillPoly(frame, [pts], color=(255, 255, 255), lineType=cv2.LINE_AA)

def draw_click_ripple(frame, vx, vy, progress):
    """Desenha onda de choque circular no instante do clique mecânico."""
    if vx is None or vy is None:
        return
    r = int(15 + progress * 95)
    alpha = max(0.0, 1.0 - progress)
    thickness = max(1, int(4 * (1.0 - progress)))
    
    color = (0, 255, int(136 * alpha))
    cv2.circle(frame, (vx, vy), r, color, thickness, cv2.LINE_AA)
    if r > 10:
        cv2.circle(frame, (vx, vy), int(r * 0.65), (0, 230, 255), 1, cv2.LINE_AA)

class MotionGraphicsAgent:
    def __init__(self, fps=30):
        self.fps = fps

    def apply_motion_graphics(self, input_video_path, output_video_path, telemetry=None, trajectory_file=None):
        input_video_path = Path(input_video_path).resolve()
        output_video_path = Path(output_video_path).resolve()
        
        cap = cv2.VideoCapture(str(input_video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Não foi possível abrir o vídeo: {input_video_path}")
            
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or self.fps
        
        print(f"🎨 [MOTION AGENT] Processando {total_frames} frames ({width}x{height} @ {video_fps:.1f} FPS) com Zooms Dinâmicos...")
        
        # Telemetria
        click_sec = 18.0
        outcome_sec = 33.0
        profit_amount = 82
        amount = 100
        click_coords = {"x": 1855, "y": 465}
        
        action = "CALL"
        payout_pct = 82
        if telemetry:
            click_sec = telemetry.get("click_event", {}).get("second_exact", 18.0)
            outcome_sec = telemetry.get("outcome_event", {}).get("expiration_second", 50.0)
            profit_amount = telemetry.get("outcome_event", {}).get("profit_amount", 82)
            amount = telemetry.get("click_event", {}).get("investment_amount", 100)
            payout_pct = telemetry.get("click_event", {}).get("payout_pct", 82)
            click_coords = telemetry.get("click_event", {}).get("button_coords_1080p", {"x": 1855, "y": 465})
            action = telemetry.get("click_event", {}).get("action", "CALL")

        trajectory = []
        if trajectory_file and Path(trajectory_file).exists():
            with open(trajectory_file, "r", encoding="utf-8") as f:
                traj_data = json.load(f)
                trajectory = traj_data.get("trajectory", [])

        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(video_fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", str(video_fps),
            str(output_video_path)
        ]
        
        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        frame_idx = 0
        t0 = time.perf_counter()
        
        # Coordenadas base do gráfico vertical (Tier 2: Y de 160 a 1180, altura 1020)
        y_sup_base = 880
        cx_base, cy_base = 795, 760
        
        # Coordenadas do botão HIGHER no Tier 3 (Y de 1180 a 1920, altura 740)
        click_vx_base, click_vy_base, _ = map_screen_coords_to_vertical(click_coords.get("x", 1855), click_coords.get("y", 465))
        if click_vx_base is None:
            click_vx_base, click_vy_base = 964, 1596
            
        btn_rel_x = click_vx_base / 1080.0
        btn_rel_y = (click_vy_base - 1180) / 740.0
        wick_rel_x = cx_base / 1080.0
        wick_rel_y = (cy_base - 160) / 1020.0
        
        traj_idx = 0
        traj_len = len(trajectory)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            t_sec = frame_idx / video_fps
            
            # -------------------------------------------------------------
            # ZOOMS DINÂMICOS CINEMATOGRÁFICOS (Header 0..160 SEMPRE PRESERVADO)
            # -------------------------------------------------------------
            z_mid, cx_m, cy_m, z_bot, cx_b, cy_b = get_dynamic_zooms(
                t_sec, click_sec, outcome_sec,
                cx_wick_rel=wick_rel_x, cy_wick_rel=wick_rel_y,
                cx_btn_rel=btn_rel_x, cy_btn_rel=btn_rel_y
            )
            
            # Zoom no Gráfico (Middle Tier: 160..1180)
            mid_tier = frame[160:1180, :]
            zoomed_mid, mx1, my1, mcw, mch = apply_smooth_zoom(mid_tier, z_mid, cx_m, cy_m)
            frame[160:1180, :] = zoomed_mid
            
            # Zoom no Painel de Disparo (Bottom Tier: 1180..1920)
            bot_tier = frame[1180:1920, :]
            zoomed_bot, bx1, by1, bcw, bch = apply_smooth_zoom(bot_tier, z_bot, cx_b, cy_b)
            frame[1180:1920, :] = zoomed_bot
            
            # Mapeamento dinâmico dos pontos de suporte e pavio com o zoom ativo
            _, t_ysup_rel = transform_point_zoom(50, y_sup_base - 160, 1080, 1020, mx1, my1, mcw, mch)
            y_sup = 160 + t_ysup_rel
            
            t_cx, t_cy_rel = transform_point_zoom(cx_base, cy_base - 160, 1080, 1020, mx1, my1, mcw, mch)
            cx, cy = t_cx, 160 + t_cy_rel
            
            t_btn_x, t_btn_y_rel = transform_point_zoom(click_vx_base, click_vy_base - 1180, 1080, 740, bx1, by1, bcw, bch)
            click_vx, click_vy = t_btn_x, 1180 + t_btn_y_rel

            # -------------------------------------------------------------
            # 1. MOTION GRAPHICS: GANCHO & APRESENTAÇÃO
            # -------------------------------------------------------------
            if 0.5 <= t_sec <= 3.5:
                bx1_g, by1_g, bx2_g, by2_g = 260, 240, 820, 310
                sub_img = frame[by1_g:by2_g, bx1_g:bx2_g]
                black_rect = np.full(sub_img.shape, (15, 20, 30), dtype=np.uint8)
                cv2.addWeighted(sub_img, 0.2, black_rect, 0.8, 0, sub_img)
                frame[by1_g:by2_g, bx1_g:bx2_g] = sub_img
                cv2.rectangle(frame, (bx1_g, by1_g), (bx2_g, by2_g), (0, 70, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, "FALSO ROMPIMIENTO?", (bx1_g + 30, by1_g + 48),
                            cv2.FONT_HERSHEY_DUPLEX, 0.95, (0, 220, 255), 2, cv2.LINE_AA)

            # -------------------------------------------------------------
            # 2. SUPORTE CONFIRMADO & RECHAZO DE MECHA
            # -------------------------------------------------------------
            # -------------------------------------------------------------
            # 2. SUPORTE / RESISTÊNCIA & RECHAZO DE MECHA
            # -------------------------------------------------------------
            if 3.5 <= t_sec <= (click_sec - 0.5):
                # Linha animada
                progress_line = min(1.0, (t_sec - 3.5) * 2.0)
                line_end_x = int(50 + progress_line * (1030 - 50))
                line_color = (0, 230, 118) if action == "CALL" else (0, 140, 255)
                cv2.line(frame, (50, y_sup), (line_end_x, y_sup), line_color, 4, cv2.LINE_AA)
                
                # Badge Nível
                level_title = "SOPORTE CONFIRMADO" if action == "CALL" else "RESISTENCIA CONFIRMADA"
                cv2.rectangle(frame, (60, y_sup - 48), (440, y_sup - 6), (15, 20, 30), -1)
                cv2.rectangle(frame, (60, y_sup - 48), (440, y_sup - 6), line_color, 2, cv2.LINE_AA)
                cv2.putText(frame, level_title, (75, y_sup - 18),
                            cv2.FONT_HERSHEY_DUPLEX, 0.72, line_color, 2, cv2.LINE_AA)
                
                # Círculo Neon no Pavio (acompanha o zoom do pavio)
                pulse = int(4.0 * np.sin((t_sec - 3.5) * 8.0))
                r = int(60 * z_mid) + pulse
                cv2.circle(frame, (cx, cy), r, (0, 235, 255), 3, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), r + 4, (0, 180, 255), 1, cv2.LINE_AA)
                
                # Seta Direcional
                if action == "CALL":
                    arrow_start = (int(cx - 150 * z_mid), int(cy - 100 * z_mid))
                    arrow_end = (int(cx - 35 * z_mid), int(cy - 25 * z_mid))
                    badge_wick = "RECHAZO DE MECHA"
                else:
                    arrow_start = (int(cx - 150 * z_mid), int(cy + 100 * z_mid))
                    arrow_end = (int(cx - 35 * z_mid), int(cy + 25 * z_mid))
                    badge_wick = "AGOTAMIENTO DE COMPRA"
                cv2.arrowedLine(frame, arrow_start, arrow_end, (0, 235, 255), 4, tipLength=0.25, line_type=cv2.LINE_AA)
                
                # Badge 'RECHAZO DE MECHA' / 'AGOTAMIENTO DE COMPRA'
                # Posiciona garantindo que não colida com o badge de nível à esquerda (que vai até x=440)
                badge_w = 420 if action != "CALL" else 330
                abx1 = max(460, arrow_start[0] - 120)
                abx2 = abx1 + badge_w
                if abx2 > 1050:
                    abx1 = 1050 - badge_w
                    abx2 = 1050
                aby1 = arrow_start[1] - 45 if action == "CALL" else arrow_start[1] + 20
                aby2 = aby1 + 45
                cv2.rectangle(frame, (abx1, aby1), (abx2, aby2), (15, 20, 30), -1)
                cv2.rectangle(frame, (abx1, aby1), (abx2, aby2), (0, 235, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, badge_wick, (abx1 + 15, aby1 + 31),
                            cv2.FONT_HERSHEY_DUPLEX, 0.62, (255, 255, 255), 2, cv2.LINE_AA)

            # -------------------------------------------------------------
            # 3. DISPARO SNIPER NO CLIQUE
            # -------------------------------------------------------------
            if (click_sec - 1.0) <= t_sec <= (click_sec + 4.5):
                cv2.line(frame, (50, y_sup), (1030, y_sup), (0, 180, 80) if action == "CALL" else (0, 100, 220), 2, cv2.LINE_AA)
                sbx1, sby1, sbx2, sby2 = 600, 480, 1040, 540
                box_color = (0, 200, 80) if action == "CALL" else (0, 80, 220)
                cv2.rectangle(frame, (sbx1, sby1), (sbx2, sby2), box_color, -1)
                cv2.rectangle(frame, (sbx1, sby1), (sbx2, sby2), (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"SEGUNDO 31 // {action} ${amount}", (sbx1 + 18, sby1 + 40),
                            cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)

            # -------------------------------------------------------------
            # 4. TENSÃO & TASA BLINDADA
            # -------------------------------------------------------------
            if (click_sec + 4.5) < t_sec <= outcome_sec:
                line_color = (0, 230, 118) if action == "CALL" else (0, 140, 255)
                cv2.line(frame, (50, y_sup), (1030, y_sup), line_color, 3, cv2.LINE_AA)
                tbx1, tby1, tbx2, tby2 = 360, 520, 720, 575
                cv2.rectangle(frame, (tbx1, tby1), (tbx2, tby2), (20, 25, 35), -1)
                cv2.rectangle(frame, (tbx1, tby1), (tbx2, tby2), line_color, 2, cv2.LINE_AA)
                tens_title = "TASA BLINDADA" if action == "CALL" else "FLUJO CONFIRMADO"
                cv2.putText(frame, tens_title, (tbx1 + 30, tby1 + 38),
                            cv2.FONT_HERSHEY_DUPLEX, 0.75, line_color, 2, cv2.LINE_AA)

            # -------------------------------------------------------------
            # 5. WIN & DOPAMINA (após expiração)
            # -------------------------------------------------------------
            if t_sec > outcome_sec:
                wbx1, wby1, wbx2, wby2 = 220, 450, 860, 550
                cv2.rectangle(frame, (wbx1, wby1), (wbx2, wby2), (0, 160, 60), -1)
                cv2.rectangle(frame, (wbx1, wby1), (wbx2, wby2), (0, 255, 136), 3, cv2.LINE_AA)
                cv2.putText(frame, f"+${profit_amount} AL BOLSILLO", (wbx1 + 40, wby1 + 65),
                            cv2.FONT_HERSHEY_DUPLEX, 1.15, (255, 255, 255), 3, cv2.LINE_AA)

            # -------------------------------------------------------------
            # 5.5 HUD OPERACIONAL DO TIER 3 (SALDO E MOMENTO CALL/PUT)
            # -------------------------------------------------------------
            self._draw_tier3_hud(frame, t_sec, click_sec, outcome_sec, action, amount, payout_pct, profit_amount)

            # -------------------------------------------------------------
            # 6. RENDERIZAÇÃO DO MOUSE & ONDA DE CLIQUE
            # -------------------------------------------------------------
            cur_vx, cur_vy = None, None
            
            if traj_len > 0:
                while traj_idx < traj_len - 1 and trajectory[traj_idx]["t"] < t_sec:
                    traj_idx += 1
                pt_cur = trajectory[traj_idx]
                cur_vx, cur_vy, _ = map_screen_coords_to_vertical(pt_cur["x"], pt_cur["y"])
            else:
                if t_sec < 4.0:
                    p = min(1.0, t_sec / 4.0)
                    cur_vx = int(586 + 80 * np.sin(p * np.pi))
                    cur_vy = int(756 - 60 * np.cos(p * np.pi))
                elif 4.0 <= t_sec < 10.0:
                    cur_vx = int(350 + 200 * np.sin((t_sec - 4.0) * 1.2))
                    cur_vy = int(y_sup_base - 25)
                elif 10.0 <= t_sec < (click_sec - 2.5):
                    angle = (t_sec - 10.0) * 3.0
                    cur_vx = int(cx_base + 45 * np.cos(angle))
                    cur_vy = int(cy_base + 45 * np.sin(angle))
                elif (click_sec - 2.5) <= t_sec < click_sec:
                    p = (t_sec - (click_sec - 2.5)) / 2.5
                    cur_vx = int(cx_base + p * (click_vx_base - cx_base))
                    cur_vy = int(cy_base + p * (click_vy_base - cy_base))
                elif click_sec <= t_sec <= (click_sec + 0.6):
                    cur_vx, cur_vy = click_vx_base, click_vy_base
                else:
                    p = min(1.0, (t_sec - (click_sec + 0.6)) / 2.0)
                    cur_vx = int(click_vx_base + p * (586 - click_vx_base))
                    cur_vy = int(click_vy_base + p * (756 - click_vy_base))

            # Transformar coordenadas do cursor se o tier estiver em zoom
            if cur_vx is not None and cur_vy is not None:
                if 160 <= cur_vy < 1180 and z_mid > 1.001:
                    tx, ty_rel = transform_point_zoom(cur_vx, cur_vy - 160, 1080, 1020, mx1, my1, mcw, mch)
                    cur_vx, cur_vy = tx, 160 + ty_rel
                elif cur_vy >= 1180 and z_bot > 1.001:
                    bx, by_rel = transform_point_zoom(cur_vx, cur_vy - 1180, 1080, 740, bx1, by1, bcw, bch)
                    cur_vx, cur_vy = bx, 1180 + by_rel
                draw_cursor_pointer(frame, cur_vx, cur_vy, highlight=True)

            # Desenhar onda de choque no momento do clique mecânico
            if click_sec <= t_sec <= (click_sec + 0.6):
                ripple_prog = (t_sec - click_sec) / 0.6
                draw_click_ripple(frame, click_vx, click_vy, ripple_prog)
                
            proc.stdin.write(frame.tobytes())
            frame_idx += 1
            
        cap.release()
        proc.stdin.close()
        proc.wait()
        
        dt = time.perf_counter() - t0
        print(f"✅ [MOTION AGENT] Renderização de motion, zooms e mouse concluída em {dt:.2f}s ({frame_idx/dt:.1f} FPS)")
        return output_video_path

    def _draw_tier3_hud(self, frame, t_sec, click_sec, outcome_sec, action, amount, payout_pct, profit_amount):
        """
        Renderiza o HUD Operacional e de Saldo no Tier 3 (inferior esquerdo, x: 0..570, y: 1205..1545).
        Cobre qualquer texto cortado na margem e exibe o saldo grande e legível para mobile sem cortes.
        """
        hud_x1, hud_y1, hud_x2, hud_y2 = 0, 1205, 570, 1545
        
        # Determinar estágio do trade
        if t_sec < click_sec:
            stage = "INIT"
            current_balance = f"${amount}.00"
            dot_color = (0, 255, 136)
            stage_title = "ANALIZANDO MERCADO"
            btn_color = (40, 50, 70)
            label_action = "ESPERANDO CONFIRMACION"
            sub_action = f"GATILLO EN SEGUNDO 31 // {action}"
            payout_txt = f"PAYOUT OFICIAL: +{payout_pct}%"
        elif t_sec <= outcome_sec:
            stage = "ACTIVE"
            current_balance = "$0.00"
            dot_color = (0, 140, 255)
            stage_title = "EN OPERACION (CAPITAL EN RIESGO)"
            btn_color = (0, 60, 220) if action == "PUT" else (0, 180, 70)
            label_action = f"MOMENTO: {action} (LOWER)" if action == "PUT" else f"MOMENTO: {action} (HIGHER)"
            sub_action = f"DISPARO: ${amount} // SEGUNDO 31"
            payout_txt = f"LUCRO ESTIMADO: +${profit_amount}.00"
        else:
            stage = "WIN"
            final_total = amount + profit_amount
            current_balance = f"${final_total}.00"
            dot_color = (0, 255, 136)
            stage_title = "OPERACION GANADA"
            btn_color = (0, 180, 70)
            label_action = f"VICTORIA: {action} CONFIRMADO"
            sub_action = f"+${profit_amount}.00 AL BOLSILLO"
            payout_txt = f"SALDO ACTUALIZADO: ${final_total}.00"

        # 1. Background sólido oficial IQ Option Dark Navy
        bg_color = (25, 20, 15)
        cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y2), bg_color, -1)
        
        # Borda refinada
        border_color = (0, 255, 136) if stage == "WIN" else (0, 215, 255)
        cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y2), border_color, 2, cv2.LINE_AA)
        
        # Topo do HUD: Cabeçalho do Card
        cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y1 + 155), (32, 25, 20), -1)
        cv2.line(frame, (hud_x1, hud_y1 + 155), (hud_x2, hud_y1 + 155), (60, 50, 42), 1, cv2.LINE_AA)
        
        # Status Saldo
        cv2.circle(frame, (hud_x1 + 25, hud_y1 + 35), 7, dot_color, -1, cv2.LINE_AA)
        cv2.putText(frame, "SALDO EN CUENTA", (hud_x1 + 45, hud_y1 + 42), cv2.FONT_HERSHEY_DUPLEX, 0.65, (180, 200, 220), 1, cv2.LINE_AA)
        
        # Saldo Valor (Gigante e sem cortes)
        bal_color = (0, 255, 136) if stage == "WIN" else (255, 255, 255)
        cv2.putText(frame, current_balance, (hud_x1 + 25, hud_y1 + 105), cv2.FONT_HERSHEY_DUPLEX, 1.30, bal_color, 3, cv2.LINE_AA)
        cv2.putText(frame, "USD", (hud_x1 + 280, hud_y1 + 105), cv2.FONT_HERSHEY_DUPLEX, 0.70, (0, 215, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "ACTIVO: PEN/USD (OTC) DIGITAL", (hud_x1 + 25, hud_y1 + 138), cv2.FONT_HERSHEY_DUPLEX, 0.50, (150, 165, 185), 1, cv2.LINE_AA)
        
        # 2. Seção do Momento de Operação (CALL / PUT)
        cv2.rectangle(frame, (hud_x1 + 15, hud_y1 + 175), (hud_x2 - 15, hud_y1 + 230), btn_color, -1)
        cv2.rectangle(frame, (hud_x1 + 15, hud_y1 + 175), (hud_x2 - 15, hud_y1 + 230), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, label_action, (hud_x1 + 25, hud_y1 + 212), cv2.FONT_HERSHEY_DUPLEX, 0.70, (255, 255, 255), 2, cv2.LINE_AA)
        
        # Detalhes da Ordem
        cv2.putText(frame, sub_action, (hud_x1 + 25, hud_y1 + 270), cv2.FONT_HERSHEY_DUPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, payout_txt, (hud_x1 + 25, hud_y1 + 310), cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 230, 118), 1, cv2.LINE_AA)

if __name__ == "__main__":
    agent = MotionGraphicsAgent()
    print("MotionGraphicsAgent atualizado com renderização de zooms dinâmicos, cursor e HUD Tier 3.")
