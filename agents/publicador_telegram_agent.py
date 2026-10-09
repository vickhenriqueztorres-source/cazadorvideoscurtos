#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: PublicadorTelegramAgent (Etapa 4)
Exportação e Disparo para o Telegram (@studiodocsyt_bot)
Envia o Short final (1080x1920 @ 60 FPS) diretamente para aprovação do líder.
=============================================================================
"""

import sys
import os
import json
import urllib.request
import urllib.parse
from pathlib import Path

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TELEGRAM_BOT_TOKEN = "8834356238:AAFSTaaMPLOVaHOXRDsox8aVaNnIBbida3g"
TELEGRAM_CHAT_ID = "5545230354"

class PublicadorTelegramAgent:
    def __init__(self, token=TELEGRAM_BOT_TOKEN, chat_id=TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text):
        """Envia mensagem de texto formatada."""
        url = f"{self.base_url}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[AVISO TELEGRAM] Falha ao enviar mensagem: {e}")
            return None

    def send_video_preview(self, video_path, caption=""):
        """Envia o arquivo MP4 para o Telegram com multipart/form-data."""
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")
            
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        url = f"{self.base_url}/sendVideo"
        
        # Build multipart body
        body_parts = []
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{self.chat_id}\r\n".encode("utf-8"))
        if caption:
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
            body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nMarkdown\r\n".encode("utf-8"))
            
        # File field
        filename = video_path.name
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{filename}\"\r\nContent-Type: video/mp4\r\n\r\n".encode("utf-8"))
        
        with open(video_path, "rb") as f:
            file_data = f.read()
            
        body_parts.append(file_data)
        body_parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        
        full_body = b"".join(body_parts)
        
        req = urllib.request.Request(url, data=full_body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(full_body)))
        
        try:
            print(f"📤 Enviando vídeo ({len(full_body) / (1024*1024):.2f} MB) para o Telegram...")
            with urllib.request.urlopen(req, timeout=60) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                if res.get("ok"):
                    print(f"✅ [TELEGRAM] Vídeo entregue com sucesso no chat {self.chat_id}!")
                    return res
                else:
                    print(f"❌ [TELEGRAM ERROR] {res}")
                    return None
        except Exception as e:
            print(f"[ERRO TELEGRAM ENVIO] {e}")
            return None

    def publish_take(self, video_file, telemetry_file=None):
        video_file = Path(video_file).resolve()
        caption_lines = [
            "🎯 *EL CAZADOR DEL WINS // NOVO SHORT PRONTO!*",
            f"📹 *Arquivo:* `{video_file.name}`",
            "📱 *Formato:* 9:16 (1080x1920) @ 60 FPS",
            "🔊 *Áudio:* Voz es-419 + SFX Sincronizados",
            "⚡ *Status:* Pronto para aprovação e postagem!"
        ]
        
        if telemetry_file and Path(telemetry_file).exists():
            with open(telemetry_file, "r", encoding="utf-8") as f:
                t = json.load(f)
                click_sec = t.get("click_event", {}).get("second_exact", 12.35)
                act = t.get("click_event", {}).get("action", "CALL")
                profit = t.get("outcome_event", {}).get("profit_amount", 870)
                caption_lines.insert(2, f"⚡ *Operação:* {act} ($1.000) às {click_sec}s -> WIN (+${profit})")
                
        caption = "\n".join(caption_lines)
        return self.send_video_preview(video_file, caption)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PublicadorTelegramAgent - Envio de Shorts")
    parser.add_argument("--video", required=True, help="Caminho do vídeo final MP4")
    parser.add_argument("--telemetry", help="Caminho do arquivo de telemetria")
    args = parser.parse_args()
    
    agent = PublicadorTelegramAgent()
    agent.publish_take(args.video, args.telemetry)
