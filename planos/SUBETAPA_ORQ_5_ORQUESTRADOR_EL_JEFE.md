# SUBETAPA 5: O ORQUESTRADOR GERAL (EL JEFE)
**Arquivo:** `orchestrator/el_jefe_pipeline.py`  
**Objetivo:** Executar de ponta a ponta as 4 etapas da esteira com comando único, tratando erros e gerando os vídeos prontos.

---

## 1. Fluxo de Execução
```powershell
python "D:\cazador - videos curtos\orchestrator\el_jefe_pipeline.py" --action CALL --amount 1000 --publish-telegram
```

## 2. Pipeline Interno:
1. `CazadorRecorderAgent.run_take()` -> Gera vídeo master + telemetria.
2. `GuionistaVozAgent.generate_narration()` -> Gera roteiro e TTS em espanhol.
3. `EditorCazadorAgent.assemble_short()` -> Aplica zooms, SFX e renderiza vídeo final 9:16 @ 60 FPS.
4. `PublicadorTelegramAgent.send_preview()` -> Notifica e envia o vídeo no Telegram.
