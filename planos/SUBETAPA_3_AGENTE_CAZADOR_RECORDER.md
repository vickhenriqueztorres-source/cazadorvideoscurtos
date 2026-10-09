# SUBETAPA 3: O AGENTE EXECUTOR (`cazador_recorder_agent.py`)
**Agente Responsável:** `CazadorRecorderAgent`  
**Localização:** `D:\cazador - videos curtos\agents\cazador_recorder_agent.py`  
**Objetivo:** Orquestrar o ciclo de vida completo de gravação de tela a 60 FPS, automação cirúrgica com mouse humano e geração de telemetria sincronizada.  
**Status:** Pronto para Implementação de Código  

---

## 1. Módulos Internos do Agente

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      MÓDULOS DO CAZADOR RECORDER AGENT                           │
├─────────────────────┬────────────────────────────────────────────────────────────┤
│ Driver de Viewport  │ Garante a janela da IQ Option em Full Screen 1080p nativo  │
│                     │ com recorte centralizado 9:16 pré-configurado.             │
├─────────────────────┼────────────────────────────────────────────────────────────┤
│ Motor de Captura    │ Thread dedicada operando MSS + Pipe FFmpeg acelerado por   │
│ (screen_recorder)   │ hardware para gravação sustentada em 60.0 FPS reais.       │
├─────────────────────┼────────────────────────────────────────────────────────────┤
│ Automação de Clique │ Preenche $1.000, aguarda janela de 10s-12s, move o cursor  │
│                     │ suavemente e dispara pyautogui.click() registrando timestamp│
├─────────────────────┼────────────────────────────────────────────────────────────┤
│ Gerador Telemetria  │ Monitora a expiração de 30s, encerra o stream e grava      │
│                     │ o take_XXXX_telemetry.json sincronizado com o MP4.         │
└─────────────────────┴────────────────────────────────────────────────────────────┘
```

---

## 2. Roteiro Temporal do Take (28 a 34 Segundos)

```
00:00s ── Início da Gravação 60 FPS (Buffer inicial limpo)
  │
00:02s ── Análise visual dos candles de 5 segundos
  │
00:06s ── Verificação das Bandas de Bollinger / Payout
  │
00:10s ── Início do movimento humano e suave do mouse em direção ao botão CALL/PUT
  │
00:12s ── Disparo cirúrgico do clique (click_event registrado em milissegundos)
  │       Linha tracejada de entrada aparece no gráfico
  │
00:13s ── Cursor se afasta suavemente para o centro do gráfico
  │
00:27s ── Fim dos 30s de expiração da ordem
  │       Resultado da vitória confirmado (outcome_event WIN registrado)
  │
00:30s ── Encerramento do stream de vídeo e salvamento dos arquivos
```

---

## 3. Procedimento de Teste e Debug Real

1. Execução de ensaio sem gravação para validar o relógio temporal:
   ```powershell
   python "D:\cazador - videos curtos\agents\cazador_recorder_agent.py" --dry-run
   ```
2. Execução de take real completo de 30 segundos:
   ```powershell
   python "D:\cazador - videos curtos\agents\cazador_recorder_agent.py" --duration 30 --action CALL
   ```
3. Auditoria do take via QA Gate:
   ```powershell
   python "D:\cazador - videos curtos\scripts\qa_validator.py" --take-dir "D:\cazador - videos curtos\staging\take_exemplo"
   ```

---

## 4. Critérios de Aceite para Homologação da Subetapa 3
- [ ] Vídeo MP4 gerado com duração entre 28s e 34s e taxa de quadros de 60.0 FPS.
- [ ] Arquivo `take_XXXX_telemetry.json` contendo `click_event` entre 10s e 12s.
- [ ] Mouse visível na gravação durante o movimento para o botão.
- [ ] Take homologado e transferido para `raw_recordings/`.
