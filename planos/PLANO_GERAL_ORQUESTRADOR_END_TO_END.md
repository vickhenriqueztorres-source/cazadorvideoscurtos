# PLANO GERAL: ORQUESTRADOR END-TO-END — EL CAZADOR DEL WINS
**Canal:** El Cazador del Wins (@elcazadordelwins)  
**Formato:** Shorts / Reels / TikTok (Vertical 9:16 @ 60 FPS)  
**Duração Alvo:** 26 a 32 segundos (Retenção > 115% e loop infinito)  
**Status:** Em Implementação Progressiva  

---

## 1. Squad de Agentes Especializados da Esteira

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│              SQUAD MULTI-AGENTE DO PIPELINE (EL CAZADOR DEL WINS)                │
└──────────────────────────────────────────────────────────────────────────────────┘

                  ┌─────────────────────────────────────┐
                  │ 0. EL JEFE (Orquestrador do Pipeline)│
                  │   orchestrator/el_jefe_pipeline.py  │
                  └──────────────────┬──────────────────┘
                                     │
      ┌──────────────────────────────┼──────────────────────────────┐
      │                              │                              │
      ▼                              ▼                              ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ 1. GRAVAÇÃO &    │       │ 2. GUIONISTA &   │       │ 3. EDITOR &      │
│ TELEMETRIA       │──────►│ VOZ ES-419       │──────►│ MONTAGEM 60 FPS  │──────►
│ CazadorRecorder  │       │ GuionistaVoz     │       │ EditorCazador    │
└──────────────────┘       └──────────────────┘       └──────────────────┘
                                                                    │
                                                                    ▼
                                                          ┌──────────────────┐
                                                          │ 4. PUBLICADOR &  │
                                                          │ FILA TELEGRAM    │
                                                          │ PublicadorTelegram
                                                          └──────────────────┘
```

| Agente | Arquivo / Módulo | Responsabilidade |
|---|---|---|
| **0. EL JEFE** | `orchestrator/el_jefe_pipeline.py` | Orquestrador Mestre: executa a esteira ponta a ponta, gerencia estados (`PENDING`, `RECORDED`, `VOICED`, `RENDERED`, `PUBLISHED`), recupera falhas e envia relatórios. |
| **1. CazadorRecorder** | `agents/cazador_recorder_agent.py` | Gravação automatizada da IQ Option em 9:16 a 60 FPS com telemetria exata do clique e resultado. |
| **2. GuionistaVoz** | `agents/guionista_voz_agent.py` | Criação do roteiro em 5 atos (50-60 palavras em espanhol neutro es-419) e geração do áudio TTS neural com pausas calibradas. |
| **3. EditorCazador** | `agents/editor_cazador_agent.py` | Montagem e efeitos de dopamina: sincronização de zoom no milissegundo do clique, inserção dos SFX (impacto, mouse click, heartbeat, cash), legendas dinâmicas e renderização 1080x1920 @ 60 FPS. |
| **4. PublicadorTelegram** | `agents/publicador_telegram_agent.py` | Conexão com o bot do Telegram (@studiodocsyt_bot), envio do MP4 final, telemetria resumida e botões de aprovação com 1 clique. |

---

## 2. A Coreografia Psicológica e Picos de Dopamina (5 Fases)

O vídeo é construído sob uma régua de tensão rigorosa para reter mais de 115% da audiência:

```
00s ─── [FASE 1: O GANCHO DE QUEBRA DE PADRÃO] (00s a 04s)
        Vela caindo forte em suporte. Frase de choque + Impacto grave (Thud).
        "El noventa y nueve por ciento va a vender aquí..."
        
05s ─── [FASE 2: A TENSÃO DO SETUP] (05s a 11s)
        Vela toca zona e deixa mecha. Zoom na mecha + Círculo neon.
        "El cazador espera el rechazo, no el precio."
        
12s ─── [FASE 3: O MOMENTO DO DISPARO] (12s a 15s)
        3s finais do relógio. Zoom violento no botão SUBIR/CALL.
        Silêncio na voz + Clique mecânico seco do mouse + Linha tracejada verde.
        
16s ─── [FASE 4: A CORRIDA DO TEMPO / QUASE PERDEU] (16s a 24s)
        Oscilação perigosa perto da taxa de entrada. Câmera recua e mostra $1.000.
        Som tenso de Heartbeat (batimentos cardíacos) acelerando.
        
25s ─── [FASE 5: A RECOMPENSA / VITÓRIA EXPLOSIVA] (25s a 30s)
        Explosão para cima + Efeito shake + Popup verde neon com lucro: +$870.00.
        Som de caixa registradora e moedas (Cash Ding).
        Narrador: "Ochocientos setenta al bolsillo. Sigue al Cazador para operar así."
```

---

## 3. As 4 Etapas Automatizadas da Esteira

1. **Etapa 1: Gravação e Telemetria:** Robô IQ Option grava em 9:16 a 60 FPS, clica entre 10s-12s e exporta `take_XXXX.mp4` e `take_XXXX_telemetry.json` para `raw_recordings/`. *(HOMOLOGADA E VALIDADA)*
2. **Etapa 2: Narração e Voz:** Roteiro em 5 atos sincronizado com os timestamps do take. Síntese com `edge_tts` (`es-MX-JorgeNeural` es-419) gerando `voice.mp3`.
3. **Etapa 3: Montagem e Dopamina:** Ingestão de `video_master.mp4` + `telemetry.json` + `voice.mp3` + SFX. Aplicação de zoom in cirúrgico no exato milissegundo do clique, inserção de áudios e renderização do vídeo final 1080x1920 @ 60 FPS em `output_shorts/`.
4. **Etapa 4: Fila e Telegram:** Envio direto do arquivo MP4 para o Telegram com ficha técnica do trade e status de prontidão.

---

## 4. Governança de Validação e Transição

Cada etapa será implementada, testada isoladamente com debug real e certificada antes de prosseguir. Ao final, o script `orchestrator/el_jefe_pipeline.py` unificará todas as 4 etapas com um comando único.
