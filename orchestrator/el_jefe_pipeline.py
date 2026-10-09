#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // ORQUESTRADOR CENTRAL: EL JEFE
Executa a esteira de ponta a ponta:
Etapa 1: Gravação de Tela 60 FPS + Telemetria (CazadorRecorderAgent)
Etapa 2: Roteiro & Narração es-419 (GuionistaVozAgent)
Etapa 3: Montagem, Zooms & SFX de Dopamina (EditorCazadorAgent)
Etapa 4: Fila e Entrega no Telegram (PublicadorTelegramAgent)
=============================================================================
"""

import sys
import os
import time
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
sys.path.append(str(BASE_DIR / "agents"))
sys.path.append(str(BASE_DIR / "scripts"))

from cazador_recorder_agent import CazadorRecorderAgent
from guionista_voz_agent import GuionistaVozAgent
from editor_cazador_agent import EditorCazadorAgent
from auditor_cazador_agent import AuditorCazadorAgent
from publicador_telegram_agent import PublicadorTelegramAgent

class ElJefePipeline:
    def __init__(self, action="AUTO", amount=100, duration=53, publish_telegram=True, theme="rechazo_pavio_m1", max_retries=3):
        self.action = action
        self.amount = amount
        self.duration = duration
        self.publish_telegram = publish_telegram
        self.theme = theme
        self.max_retries = max_retries
        
        self.recorder = CazadorRecorderAgent(action=self.action, investment_amount=self.amount, payout_pct=82, total_duration=self.duration)
        self.guionista = GuionistaVozAgent()
        self.editor = EditorCazadorAgent()
        self.auditor = AuditorCazadorAgent()
        self.publicador = PublicadorTelegramAgent()

    def run_pipeline(self):
        print("============================================================================")
        print("       🎯 EL CAZADOR DEL WINS // ESTEIRA EL JEFE (END-TO-END)")
        print("       Produção Automatizada de Shorts 9:16 @ 60 FPS (es-419)")
        print("       Com Auditoria Visual Pós-Produção (AuditorCazadorAgent)")
        print("============================================================================")
        t_global_start = time.perf_counter()

        for attempt in range(1, self.max_retries + 1):
            if self.max_retries > 1:
                print(f"\n🔄 [TENTATIVA DE PRODUÇÃO {attempt}/{self.max_retries}]")
                
            # -------------------------------------------------------------
            # ETAPA 1: GRAVAÇÃO DA TELA E TELEMETRIA
            # -------------------------------------------------------------
            print("\n[ETAPA 1/5] DISPARANDO GRAVAÇÃO AUTOMATIZADA DA TELA...")
            success, take_dir = self.recorder.run_take()
            if not success:
                print("[FALHA ETAPA 1] A gravação não passou no QA Gate inicial. Tentando novamente...")
                continue
                
            take_dir = Path(take_dir)
            print(f"[ETAPA 1 CONCLUÍDA] Take homologado em: {take_dir.name}")
            
            # -------------------------------------------------------------
            # ETAPA 2: GERAÇÃO DA NARRAÇÃO ES-419
            # -------------------------------------------------------------
            print("\n[ETAPA 2/5] DISPARANDO GERAÇÃO DA VOZ NEURAL (es-419)...")
            try:
                audio_file, script_file = self.guionista.generate_narration(take_dir, theme=self.theme)
                print(f"[ETAPA 2 CONCLUÍDA] Áudio gerado: {audio_file.name}")
            except Exception as e:
                print(f"[FALHA ETAPA 2] Erro na narração: {e}. Tentando novamente...")
                continue

            # -------------------------------------------------------------
            # ETAPA 3: MONTAGEM, ZOOMS E SFX DE DOPAMINA
            # -------------------------------------------------------------
            print("\n[ETAPA 3/5] DISPARANDO MONTAGEM 60 FPS COM EFEITOS DE DOPAMINA...")
            try:
                final_video = self.editor.assemble_short(take_dir)
                print(f"[ETAPA 3 CONCLUÍDA] Vídeo final renderizado: {final_video.name}")
            except Exception as e:
                print(f"[FALHA ETAPA 3] Erro na montagem: {e}. Tentando novamente...")
                continue

            # -------------------------------------------------------------
            # ETAPA 4: AUDITORIA RIGOROSA PÓS-PRODUÇÃO (AuditorCazadorAgent)
            # -------------------------------------------------------------
            print("\n[ETAPA 4/5] DISPARANDO AUDITORIA RIGOROSA DE QUALIDADE PÓS-PRODUÇÃO...")
            telemetry_file = take_dir / f"{take_dir.name}_telemetry.json"
            if not telemetry_file.exists():
                telemetry_file = take_dir / "telemetry.json"

            audit_passed, audit_report = self.auditor.audit_video(
                final_video,
                telemetry_path=telemetry_file,
                take_dir=take_dir
            )

            if not audit_passed:
                print(f"⚠️ [AUDITORIA REPROVOU O TAKE] Erros detectados: {audit_report.get('errors')}")
                print(f"🔄 Isolando take {take_dir.name} e reiniciando esteira para novo disparo...")
                quar_dest = BASE_DIR / "quarantine" / take_dir.name
                if quar_dest.exists():
                    shutil.rmtree(quar_dest)
                shutil.move(str(take_dir), str(quar_dest))
                continue

            print("[ETAPA 4 CONCLUÍDA] Auditoria Aprovada com Sucesso (Nota 100/100)!")

            # -------------------------------------------------------------
            # ETAPA 5: EXPORTAÇÃO E DISPARO TELEGRAM
            # -------------------------------------------------------------
            if self.publish_telegram:
                print("\n[ETAPA 5/5] ENVIANDO PRÉVIA HOMOLOGADA PARA O TELEGRAM...")
                res = self.publicador.publish_take(final_video, telemetry_file)
                if res and res.get("ok"):
                    print("[ETAPA 5 CONCLUÍDA] Vídeo entregue no Telegram com sucesso!")
                else:
                    print("[AVISO ETAPA 5] Não foi possível entregar no Telegram.")

            t_total = time.perf_counter() - t_global_start
            print("\n============================================================================")
            print(f"🏆 [PIPELINE FINALIZADO COM SUCESSO] Tempo total: {t_total:.1f} segundos")
            print(f"📁 Vídeo Final Auditado e Disponível em: {final_video}")
            print("============================================================================")
            return True, final_video

        print("\n❌ [PIPELINE ABORTADO] Número máximo de tentativas atingido sem aprovação total.")
        return False, None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orquestrador El Jefe - Produção Automatizada")
    parser.add_argument("--action", choices=["CALL", "PUT", "AUTO"], default="AUTO", help="Direção da ordem")
    parser.add_argument("--amount", type=int, default=100, help="Valor do investimento")
    parser.add_argument("--duration", type=int, default=53, help="Duração total do take")
    parser.add_argument("--theme", choices=["digital_vs_binarias", "velas_5s_roleta", "otc_algoritmo", "arbol_navidad", "rechazo_pavio_m1"], default="rechazo_pavio_m1", help="Forçar tema específico da Bíblia do Cazador")
    parser.add_argument("--no-telegram", action="store_true", help="Desativa envio para o Telegram")
    args = parser.parse_args()
    
    el_jefe = ElJefePipeline(
        action=args.action,
        amount=args.amount,
        duration=args.duration,
        publish_telegram=not args.no_telegram,
        theme=args.theme
    )
    success, video = el_jefe.run_pipeline()
    sys.exit(0 if success else 1)
