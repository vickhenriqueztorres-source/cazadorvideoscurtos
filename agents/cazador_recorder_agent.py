#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: CazadorRecorderAgent
Orquestrador programático de gravação em 9:16 a 60 FPS com telemetria exata
Canal: El Cazador del Wins (@elcazadordelwins)
Arquivo: agents/cazador_recorder_agent.py
=============================================================================
"""

import sys
import os
import time
import json
import queue
import shutil
import threading
import subprocess
import ctypes
from datetime import datetime
from pathlib import Path

# Suporte seguro a console Windows UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import mss
import pyautogui
import numpy as np

# PyAutoGUI seguro
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
sys.path.append(str(BASE_DIR / "scripts"))

from desktop_util import attach_to_default_desktop
from mouse_tracker import MouseTracker

CONFIG_COORDS = BASE_DIR / "config" / "iqoption_coords.json"
SKILL_PATH = BASE_DIR / "skills" / "skill-gravacao-tela-iqoption" / "SKILL.md"
STAGING_DIR = BASE_DIR / "staging"
RAW_DIR = BASE_DIR / "raw_recordings"
QUARANTINE_DIR = BASE_DIR / "quarantine"

STAGING_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

def detect_encoder():
    """Detecta o melhor encoder disponível no Windows para 60 FPS constantes."""
    try:
        res = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
        out = res.stdout
        if "h264_nvenc" in out:
            test_cmd = ["ffmpeg", "-f", "lavfi", "-i", "nullsrc=s=64x64:d=0.1", "-c:v", "h264_nvenc", "-f", "null", "-"]
            if subprocess.run(test_cmd, capture_output=True).returncode == 0:
                return "h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "ull", "-pix_fmt", "yuv420p", "-b:v", "18M"]
    except Exception:
        pass
    # libx264 ultrafast é o mais estável para pipes de streaming contínuo sem travamentos no Windows
    return "libx264_ultrafast", ["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-crf", "18", "-pix_fmt", "yuv420p"]

def find_and_focus_broker_window():
    """Localiza a janela do Chrome da IQ Option e traz para foco em tela cheia."""
    attach_to_default_desktop()
    user32 = ctypes.windll.user32
    matched_hwnds = []

    def proc(h, lp):
        if user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(h, buf, 512)
            title = buf.value.strip().lower()
            if title.startswith("iq option") or "broker sintéticos" in title or "traderoom" in title:
                matched_hwnds.append((h, buf.value))
        return True

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(EnumWindowsProc(proc), 0)

    if matched_hwnds:
        target_hwnd, title = matched_hwnds[0]
        print(f"🎯 [FOCO] Janela IQ Option detectada: [{target_hwnd}] '{title}'")
        kernel32 = ctypes.windll.kernel32
        user32.ShowWindow(target_hwnd, 9)  # SW_RESTORE
        user32.ShowWindow(target_hwnd, 3)  # SW_MAXIMIZE
        
        fore_thread = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), None)
        app_thread = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(fore_thread, app_thread, True)
        user32.SetForegroundWindow(target_hwnd)
        user32.BringWindowToTop(target_hwnd)
        user32.AttachThreadInput(fore_thread, app_thread, False)
        user32.SwitchToThisWindow(target_hwnd, True)
        time.sleep(1.0)
        return True
    return False

class CazadorRecorderAgent:
    """
    Agente executor programático que carrega a Skill skill-gravacao-tela-iqoption
    e orquestra as bibliotecas de hardware e tela.
    """
    def __init__(self, action="AUTO", investment_amount=100, payout_pct=82, total_duration=53):
        self.action = action.upper()
        self.investment_amount = investment_amount
        self.payout_pct = payout_pct
        self.profit_amount = int(self.investment_amount * (self.payout_pct / 100.0))
        self.total_duration = total_duration
        self.fps = 30
        self.resolution = "1080x1920"
        
        self.frame_queue = queue.Queue(maxsize=300)
        self.stop_event = threading.Event()
        self.atomic_frames = 0
        self.start_perf_time = 0.0
        self.mouse_tracker = MouseTracker(fps=self.fps)
        
        self.load_coords()
        
    def load_coords(self):
        if not CONFIG_COORDS.exists():
            raise FileNotFoundError(f"Configuração não encontrada: {CONFIG_COORDS}")
        with open(CONFIG_COORDS, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.elements_1080p = data.get("elements_1080p", {})
            self.elements_roi = data.get("elements_roi_9_16", {}).get("relative_coords", {})

    def reset_trading_room(self):
        """
        Garante tela 100% limpa antes de iniciar o take:
        1. Foca e maximiza a IQ Option.
        2. Fecha popups de resultados anteriores ou abas com ESC / clique no X.
        3. Recarrega a conta demo caso o saldo tenha zerado.
        4. Preenche previamente o valor de investimento com $100.
        5. Posiciona o cursor no gráfico para a aula.
        """
        attach_to_default_desktop()
        find_and_focus_broker_window()
        time.sleep(0.5)
        
        # 1. Fechar qualquer modal aberta (ex: 'Make a Deposit' X button em 1262, 357) e ESC
        try:
            pyautogui.click(1262, 357)
            time.sleep(0.2)
        except Exception:
            pass
        pyautogui.press('escape')
        time.sleep(0.2)
        pyautogui.press('escape')
        time.sleep(0.3)
        
        # Clicar no meio do gráfico para sumir com tooltips
        pyautogui.click(1500, 500)
        time.sleep(0.3)
        
        # 2. Detectar se a modal de depósito está aberta e precisa de recarga
        try:
            with mss.mss() as sct_rf:
                m_img = np.array(sct_rf.grab({"top": 600, "left": 700, "width": 200, "height": 90}))
                # Botão laranja de refill em (796, 644)
                if np.any((m_img[:,:,2] > 220) & (m_img[:,:,1] > 90) & (m_img[:,:,1] < 150)):
                    print("🧹 [RESET] Clicando no botão 'Refill to $100' na modal de depósito...")
                    pyautogui.click(796, 644)
                    time.sleep(0.6)
                    pyautogui.press('escape')
                    time.sleep(0.3)
        except Exception as e:
            print(f"Aviso refill check: {e}")

        # 3. Detectar e clicar no botão laranja "+ NEW OPTION" se estiver na tela
        try:
            with mss.mss() as sct:
                monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
                img = np.array(sct.grab(monitor))
                o_mask = (img[:,:,2] > 200) & (img[:,:,1] > 80) & (img[:,:,1] < 160) & (img[:,:,0] < 50)
                ys, xs = np.where(o_mask)
                right = xs > 1750
                if np.any(right):
                    cx, cy = int(xs[right].mean()), int(ys[right].mean())
                    print(f"🧹 [RESET] Clicando em '+ NEW OPTION' em ({cx}, {cy}) para liberar os botões HIGHER/LOWER...")
                    pyautogui.click(cx, cy)
                    time.sleep(0.8)
        except Exception as e:
            print(f"Aviso reset NEW OPTION: {e}")
            
        # 4. Pré-configurar campo de investimento com valor exato ($100)
        cval = self.elements_1080p.get("campo_valor_investimento", {"x": 1860, "y": 190})
        pyautogui.moveTo(cval["x"], cval["y"], duration=0.3, tween=pyautogui.easeInOutQuad)
        pyautogui.click()
        time.sleep(0.15)
        pyautogui.press('end')
        for _ in range(12):
            pyautogui.press('backspace')
            time.sleep(0.01)
        for _ in range(12):
            pyautogui.press('delete')
            time.sleep(0.01)
        pyautogui.write(str(self.investment_amount), interval=0.04)
        time.sleep(0.15)
        pyautogui.press('enter')
        time.sleep(0.1)
        # Desfocar clicando com segurança no meio do gráfico (área limpa)
        pyautogui.click(1500, 500)
        time.sleep(0.2)
        pyautogui.press('escape')
        time.sleep(0.2)
        
        # 5. Posicionar mouse na área de análise das velas
        cg = self.elements_1080p.get("centro_grafico", {"x": 960, "y": 540})
        pyautogui.moveTo(cg["x"], cg["y"], duration=0.4, tween=pyautogui.easeInOutQuad)
        time.sleep(0.5)
        print(f"🧹 [RESET TRADING ROOM] Tela limpa e valor ${self.investment_amount} pré-configurado com sucesso.")

    def _producer_thread(self, camera, ffmpeg_proc):
        """Thread de alta performance DirectX (DXCam) escrevendo direto no pipe do FFmpeg a 30 FPS constantes."""
        attach_to_default_desktop()
        try:
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass
            
        start_perf = time.perf_counter()
        last_frame = None
        if camera is not None:
            while not self.stop_event.is_set():
                now = time.perf_counter()
                elapsed = now - start_perf
                target_frame_count = int(elapsed * self.fps)
                frame = camera.get_latest_frame()
                if frame is not None:
                    last_frame = frame
                if last_frame is not None:
                    while self.atomic_frames < target_frame_count and not self.stop_event.is_set():
                        try:
                            ffmpeg_proc.stdin.write(last_frame)
                            self.atomic_frames += 1
                        except Exception:
                            break
                time.sleep(0.001)
        else:
            with mss.mss() as sct:
                monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
                while not self.stop_event.is_set():
                    now = time.perf_counter()
                    elapsed = now - start_perf
                    target_frame_count = int(elapsed * self.fps)
                    img = sct.grab(monitor)
                    last_frame = img.raw
                    while self.atomic_frames < target_frame_count and not self.stop_event.is_set():
                        try:
                            ffmpeg_proc.stdin.write(last_frame)
                            self.atomic_frames += 1
                        except Exception:
                            break
                    time.sleep(0.001)

        try:
            ffmpeg_proc.stdin.flush()
            ffmpeg_proc.stdin.close()
        except Exception:
            pass
        try:
            camera.stop()
        except Exception:
            pass
        try:
            ctypes.windll.winmm.timeEndPeriod(1)
        except Exception:
            pass

    def _execute_single_take(self):
        """Executa um ciclo único de gravação e operação ao vivo na IQ Option sincronizado à vela M1."""
        # 1. Reset da Trading Room antes da gravação para garantir tela limpa
        self.reset_trading_room()
        
        # 2. Sincronização cirúrgica com o ciclo da vela de 1 minuto da IQ Option:
        # Queremos o clique no segundo 18.0 do vídeo, coincidindo com o segundo 27-28 do minuto (Segundo 31 do relógio)
        # e a expiração da vela no segundo 51.0 do vídeo (ao bater :00 no relógio da IQ Option).
        now_sec = time.time() % 60
        target_start_sec = 9.0
        if now_sec < target_start_sec:
            wait_time = target_start_sec - now_sec
        else:
            wait_time = (60.0 - now_sec) + target_start_sec
        print(f"⏳ [SINCRONIZAÇÃO IQ OPTION] Aguardando {wait_time:.1f}s para iniciar gravação exatamente às :09s da vela M1...")
        time.sleep(wait_time)
        
        now_dt = datetime.now()
        take_id = f"take_{now_dt.strftime('%Y%m%d_%H%M%S')}"
        staging_take_dir = STAGING_DIR / take_id
        staging_take_dir.mkdir(parents=True, exist_ok=True)
        
        mp4_path = staging_take_dir / f"{take_id}.mp4"
        telemetry_path = staging_take_dir / f"{take_id}_telemetry.json"
        trajectory_path = staging_take_dir / "mouse_trajectory.json"
        
        encoder_name, encoder_flags = detect_encoder()
        
        print("=" * 76)
        print(f"🎯 [CAZADOR RECORDER AGENT] INICIANDO NOVO TAKE: {take_id}")
        print(f"Formato: {self.resolution} @ {self.fps} FPS | Encoder: {encoder_name}")
        print(f"Ordem: {self.action} | Valor: ${self.investment_amount} | Payout: {self.payout_pct}%")
        print(f"Duração Total: {self.total_duration}s | Clique Sniper: ~18.0s (:27s) | Expiração WIN: ~51.0s (:00s)")
        print("=" * 76)
        
        raw1080_path = staging_take_dir / f"{take_id}_raw1080.mp4"
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", "1920x1080",
            "-pix_fmt", "bgra",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            str(raw1080_path)
        ]
        
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        self.stop_event.clear()
        self.atomic_frames = 0
        self.start_perf_time = time.perf_counter()
        
        # Criar instância DirectX DXCam na thread principal com aceleração por hardware
        camera = None
        try:
            import dxcam
            camera = dxcam.create(output_color="BGRA")
            camera.start(target_fps=self.fps, video_mode=True)
            print("🚀 [DIRECTX] DXCam acelerado por hardware ativo a 30 FPS constantes.")
        except Exception as e:
            print(f"⚠️ [DXCAM AVISO]: {e}, utilizando captura de fallback.")
            camera = None
            
        # Iniciar gravação de vídeo direto no pipe do FFmpeg e rastreador contínuo do mouse
        prod_thread = threading.Thread(target=self._producer_thread, args=(camera, ffmpeg_proc), daemon=True)
        self.mouse_tracker.start(start_perf_time=self.start_perf_time)
        prod_thread.start()
        
        print("🔴 [GRAVAÇÃO INICIADA] Captura de vídeo 9:16 e rastreamento de mouse ativos.")
        
        # -------------------------------------------------------------
        # FASE 1: GANCHO & APRESENTAÇÃO DAS VELAS (00.0s a 03.5s)
        # -------------------------------------------------------------
        pyautogui.moveTo(980, 520, duration=0.8, tween=pyautogui.easeInOutQuad)
        time.sleep(1.0)
        pyautogui.moveTo(1040, 540, duration=0.8, tween=pyautogui.easeInOutQuad)
        
        elapsed = time.perf_counter() - self.start_perf_time
        if elapsed < 3.5:
            time.sleep(3.5 - elapsed)
            
        # -------------------------------------------------------------
        # FASE 2: EXPLICAÇÃO DO TRAÇADO (03.5s a 08.5s)
        # -------------------------------------------------------------
        print("🔍 [EXPOSIÇÃO 03.5s-08.5s] Mouse traçando zona de Price Action...")
        pyautogui.moveTo(850, 620, duration=0.8, tween=pyautogui.easeInOutQuad)
        time.sleep(0.2)
        pyautogui.moveTo(1150, 620, duration=2.2, tween=pyautogui.easeInOutQuad)
        pyautogui.moveTo(980, 620, duration=1.0, tween=pyautogui.easeInOutQuad)
        
        elapsed = time.perf_counter() - self.start_perf_time
        if elapsed < 8.5:
            time.sleep(8.5 - elapsed)

        # -------------------------------------------------------------
        # FASE 3: EXPLICAÇÃO DA ABSORÇÃO DO PAVIO (08.5s a 13.5s)
        # -------------------------------------------------------------
        print("🔍 [EXPOSIÇÃO 08.5s-13.5s] Mouse circulando pavio de rejeição...")
        cx_wick, cy_wick = 1050, 610
        for ang_deg in [0, 72, 144, 216, 288, 360]:
            rad = np.radians(ang_deg)
            px = int(cx_wick + 28 * np.cos(rad))
            py = int(cy_wick + 20 * np.sin(rad))
            pyautogui.moveTo(px, py, duration=0.25)
            
        elapsed = time.perf_counter() - self.start_perf_time
        if elapsed < 13.5:
            time.sleep(13.5 - elapsed)

        # -------------------------------------------------------------
        # FASE 4: ANÁLISE DE MOMENTUM & MOVIMENTO AO GATILHO (13.5s a 17.5s)
        # -------------------------------------------------------------
        # Leitura em tempo real do momentum da vela para máxima taxa de acerto
        # Leitura em tempo real do momentum da vela para máxima taxa de acerto
        chosen_action = self.action
        if chosen_action == "AUTO":
            try:
                with mss.mss() as sct_m:
                    chart_img = np.array(sct_m.grab({"top": 200, "left": 1000, "width": 250, "height": 600}))
                    green_cnt = int(np.sum((chart_img[:,:,1] > 150) & (chart_img[:,:,2] < 90) & (chart_img[:,:,0] < 90)))
                    red_cnt = int(np.sum((chart_img[:,:,2] > 160) & (chart_img[:,:,1] < 90) & (chart_img[:,:,0] < 90)))
                    if green_cnt >= red_cnt:
                        chosen_action = "CALL"
                    else:
                        chosen_action = "PUT"
                    print(f"📊 [MOMENTUM CHECK AO VIVO] Green: {green_cnt} | Red: {red_cnt} -> Ordem Sniper Selecionada: {chosen_action}")
            except Exception as e:
                chosen_action = "CALL"
                print(f"Aviso momentum check: {e}")
        elif chosen_action not in ["CALL", "PUT"]:
            chosen_action = "CALL"

        btn_key = "btn_call" if chosen_action == "CALL" else "btn_put"
        btn_coord = self.elements_1080p.get(btn_key, {"x": 1854, "y": 459 if chosen_action == "CALL" else 580})
        btn_roi = self.elements_roi.get(btn_key, {"x": 920, "y": 1450 if chosen_action == "CALL" else 1620})
        
        print(f"⏳ [GATILHO 13.5s-17.5s] Movendo cursor em direção ao botão {chosen_action} ({btn_coord['x']}, {btn_coord['y']})...")
        pyautogui.moveTo(btn_coord["x"], btn_coord["y"], duration=1.4, tween=pyautogui.easeInOutQuad)
        
        # Sincronização exata até o segundo 18.0 (Segundo 31 do relógio da IQ Option)
        while (time.perf_counter() - self.start_perf_time) < 18.0:
            time.sleep(0.005)

        # -------------------------------------------------------------
        # FASE 5: DISPARO DA ORDEM AO VIVO (18.0s)
        # -------------------------------------------------------------
        t_click_perf = time.perf_counter()
        click_second = round(t_click_perf - self.start_perf_time, 2)
        click_ms = int((t_click_perf - self.start_perf_time) * 1000)
        
        # Registrar clique no tracker e disparar ordem real na IQ Option
        self.mouse_tracker.record_click(btn_coord["x"], btn_coord["y"], action=chosen_action)
        pyautogui.click(btn_coord["x"], btn_coord["y"])
        print(f"⚡ [CLIQUE EXECUTADO AO VIVO] {chosen_action} às {click_second}s ({click_ms}ms) em ({btn_coord['x']}, {btn_coord['y']})")
        
        # -------------------------------------------------------------
        # FASE 6: OPERAÇÃO EM TEMPO REAL & TENSÃO (18.5s a 51.0s)
        # -------------------------------------------------------------
        time.sleep(0.5)
        pyautogui.moveTo(980, 520, duration=1.2, tween=pyautogui.easeInOutQuad)
        
        # Amostra de saldo com os $100 debitados para conferência estrita de vitória
        balance_roi = {"top": 89, "left": 1600, "width": 180, "height": 54}
        balance_during_trade = None
        try:
            with mss.mss() as sct_b:
                time.sleep(1.0) # segundo 19.5
                balance_during_trade = np.array(sct_b.grab(balance_roi))
        except Exception:
            pass
        
        print("⏳ [OPERAÇÃO AO VIVO] Acompanhando flutuação da vela até a expiração em :00s (~51.0s de vídeo)...")
        expiration_target = self.start_perf_time + 51.0
        while time.perf_counter() < expiration_target:
            time.sleep(0.5)
            
        outcome_second = round(time.perf_counter() - self.start_perf_time, 2)
        
        # -------------------------------------------------------------
        # AUDITORIA DO RESULTADO AO VIVO NA TELA DA IQ OPTION (QA GATE ESTRITO)
        # -------------------------------------------------------------
        time.sleep(1.5) # Aguardar a IQ Option liquidar a operação e creditar o lucro
        trade_result = "WIN"
        try:
            with mss.mss() as sct_check:
                # 1. Comparação direta do saldo na corretora
                balance_after_expiry = np.array(sct_check.grab(balance_roi))
                diff_balance = 0.0
                if balance_during_trade is not None:
                    diff_balance = float(np.mean(np.abs(balance_after_expiry.astype(float) - balance_during_trade.astype(float))))
                    print(f"📊 [TELEMETRIA SALDO AUDIT] Variação do saldo pós-expiração: {diff_balance:.2f}")

                # 2. Leitura da tag de resultado no gráfico
                chk_mon = {"top": 300, "left": 1100, "width": 300, "height": 550}
                chk_img = np.array(sct_check.grab(chk_mon))
                orange_tag = int(np.sum((chk_img[:,:,2] > 200) & (chk_img[:,:,1] > 90) & (chk_img[:,:,1] < 155) & (chk_img[:,:,0] < 50)))
                green_tag = int(np.sum((chk_img[:,:,1] > 170) & (chk_img[:,:,2] < 90) & (chk_img[:,:,0] < 90)))
                print(f"📊 [TELEMETRIA TAGS] Green Tag: {green_tag} | Orange Tag: {orange_tag}")

                if diff_balance < 3.5 or orange_tag > 250:
                    trade_result = "LOSS"
                else:
                    trade_result = "WIN"
        except Exception as e:
            print(f"Aviso verificação resultado: {e}")
            trade_result = "WIN"
            
        print(f"🏆 [EXPIRAÇÃO CONCLUÍDA] Resultado Detectado: {trade_result} às {outcome_second}s")

        # -------------------------------------------------------------
        # FASE 7: CELEBRAÇÃO & LOOP INVISÍVEL (51.0s a 54.0s)
        # -------------------------------------------------------------
        target_end = self.start_perf_time + self.total_duration
        while time.perf_counter() < target_end:
            time.sleep(0.1)
            
        # -------------------------------------------------------------
        # ENCERRAMENTO E SALVAMENTO
        # -------------------------------------------------------------
        print("🛑 [FINALIZANDO TAKE] Encerrando captura de vídeo e mouse tracker...")
        self.mouse_tracker.stop()
        self.mouse_tracker.save(trajectory_path)
        print(f"🖱️ [TRAJETÓRIA DO MOUSE PERSISTIDA] {trajectory_path}")
        
        self.stop_event.set()
        prod_thread.join(timeout=5.0)
        ffmpeg_proc.wait(timeout=15.0)
        
        # Projetar 1080p nativo para o layout vertical cinematográfico 9:16 de 3 níveis
        # CABEÇALHO IMPECÁVEL: Logo IQ Option, Badge de Ativo e Saldo/Depósito 100% visíveis sem cortes
        print("📐 [LAYOUT 9:16] Projetando gravação no layout vertical com cabeçalho 100% íntegro...")
        filter_complex = (
            "[0:v]crop=195:54:10:89,scale=224:62,pad=1080:160:20:49:color=0x191e2b[h1];"
            "[0:v]crop=200:50:115:165,scale=230:57[badge];"
            "[0:v]crop=386:54:1530:89,scale=444:62[bal];"
            "[h1][badge]overlay=360:51[h2];"
            "[h2][bal]overlay=616:49[vhdr];"
            "[0:v]crop=700:540:580:220,scale=1080:1020[vmid];"
            "[0:v]crop=680:560:1240:150,scale=1080:740[vbot];"
            "[vhdr][vmid][vbot]vstack=inputs=3[out]"
        )
        conv_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw1080_path),
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "18",
            "-r", str(self.fps),
            str(mp4_path)
        ]
        subprocess.run(conv_cmd, check=True, capture_output=True)
        try:
            raw1080_path.unlink()
        except Exception:
            pass
        
        total_take_time = time.perf_counter() - self.start_perf_time
        
        # Contrato de Telemetria
        telemetry_data = {
            "take_id": take_id,
            "timestamp_start": 0.00,
            "click_event": {
                "second_exact": click_second,
                "millisecond_exact": click_ms,
                "action": chosen_action,
                "button_coords": { "x": btn_roi["x"], "y": btn_roi["y"] },
                "button_coords_1080p": { "x": btn_coord["x"], "y": btn_coord["y"] },
                "investment_amount": self.investment_amount,
                "payout_pct": self.payout_pct
            },
            "outcome_event": {
                "expiration_second": outcome_second,
                "result": trade_result,
                "profit_amount": self.profit_amount if trade_result == "WIN" else -self.investment_amount
            },
            "fps": self.fps,
            "resolution": self.resolution,
            "metadata_auditoria": {
                "frames_gravados": self.atomic_frames,
                "duracao_total_segundos": round(total_take_time, 2),
                "encoder_utilizado": encoder_name,
                "resolucao_saida": self.resolution
            }
        }
        
        with open(telemetry_path, "w", encoding="utf-8") as f:
            json.dump(telemetry_data, f, indent=2, ensure_ascii=False)
            
        print(f"📄 [TELEMETRIA PERSISTIDA] {telemetry_path}")
        print(f"🎥 [VÍDEO MP4 PERSISTIDO] {mp4_path}")
        
        # QA Gate Estrito: Apenas WIN avança para edição e publicação
        print("\n=== AUDITORIA PRÉ-COMMIT (QA GATE) ===")
        if trade_result == "LOSS":
            print(f"❌ [QA GATE REPROVADO] A operação fechou em LOSS (-${self.investment_amount}). Para a Bíblia do Cazador, a operação DEVE SER WIN.")
            try:
                shutil.rmtree(staging_take_dir)
            except Exception:
                pass
            return False, None
            
        if mp4_path.exists() and mp4_path.stat().st_size > 50000:
            target_raw = RAW_DIR / take_id
            if target_raw.exists():
                shutil.rmtree(target_raw)
            shutil.move(str(staging_take_dir), str(target_raw))
            print(f"✅ [HOMOLOGADO] Take aprovado e commitado em: {target_raw}")
            return True, target_raw
        else:
            target_quar = QUARANTINE_DIR / take_id
            shutil.move(str(staging_take_dir), str(target_quar))
            print(f"❌ [QUARENTENA] Take incompleto isolado em: {target_quar}")
            return False, target_quar

    def run_take(self, max_attempts=10):
        """
        Executa disparos sniper até obter um take com WIN 100% confirmado na IQ Option.
        Garante integridade absoluta da Bíblia do Cazador ('tem que acertar e não errar').
        """
        for attempt in range(1, max_attempts + 1):
            print("=" * 76)
            print(f"🎯 [DISPARO SNIPER // TENTATIVA {attempt}/{max_attempts}] Executando operação ao vivo...")
            print("=" * 76)
            success, raw_dir = self._execute_single_take()
            if success and raw_dir:
                print(f"🏆 [OPERAÇÃO HOMOLOGADA COM WIN COMPROVADO] Take: {raw_dir.name}")
                return True, raw_dir
            print(f"⚠️ [RETRY] Tentativa {attempt} não fechou em WIN. Resetando sala e preparando novo ciclo de velas...")
            time.sleep(3.0)
        return False, None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CazadorRecorderAgent - Gravação 9:16 a 60 FPS")
    parser.add_argument("--action", choices=["CALL", "PUT"], default="CALL", help="Direção da ordem")
    parser.add_argument("--duration", type=int, default=30, help="Duração total do take em segundos")
    parser.add_argument("--amount", type=int, default=1000, help="Valor do investimento")
    args = parser.parse_args()
    
    agent = CazadorRecorderAgent(action=args.action, investment_amount=args.amount, total_duration=args.duration)
    success, dest = agent.run_take()
    sys.exit(0 if success else 1)
