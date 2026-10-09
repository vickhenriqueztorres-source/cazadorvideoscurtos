# ARQUITETURA TÉCNICA REDESENHADA: ETAPA 1 (GRAVAÇÃO, TELEMETRIA & AUTOMAÇÃO)
**Canal:** El Cazador del Wins (@elcazadordelwins) — Formato Shorts/Reels/TikTok (9:16 @ 60 FPS)  
**Projeto:** Pipeline de Produção Automatizada de Vídeos Curtos  
**Diretório Raiz:** `D:\cazador - videos curtos`  
**Versão:** 2.0.0 (Normativa e Revisada)  
**Status:** Aprovado para Implementação  

---

## 1. Sumário Executivo e Princípios de Engenharia

A **Etapa 1** é a fundação de todo o pipeline de mídia sintética do canal *El Cazador del Wins*. Sua função única e intransferível é capturar sessões operacionais da corretora IQ Option com fluidez cinematográfica (**60.0 FPS reais**), executando ações calibradas de interface (troca de velas, aplicação de tempo de 5 segundos, acionamento de ordem sniper Call/Put) e registrando telemetria cirúrgica (**sub-milissegundo**) para que as etapas posteriores de edição (Remotion / FFmpeg) possam aplicar cortes, zooms dinâmicos e sound effects com sincronia matemática perfeita.

### Princípios da Arquitetura 2.0
1. **Zero Frame Drop (Isolamento de Carga):** O Python nunca deve realizar codificação pesada de vídeo. A captura é desacoplada da compressão via filas thread-safe e pipe assíncrono para processo FFmpeg externo.
2. **Dual-Index Determinístico:** Todo evento de interface é atrelado simultaneamente ao índice sequencial inteiro do frame (`frame_index`) e ao relógio monotônico de alta precisão (`perf_counter`), erradicando qualquer desvio temporal (clock drift).
3. **Imutabilidade da Viewport:** A aplicação da corretora opera exclusivamente em resolução Desktop nativa (1920x1080), impedindo que breakpoints responsivos alterem coordenadas ou recolham painéis essenciais.
4. **Portão de QA (Fail-Fast Staging):** Nenhum take com perda de quadros, desvio de telemetria ou rejeição de ordem atinge a pasta de produção `raw_recordings/`. Gravações com anomalias são isoladas em quarentena automaticamente.

---

## 2. Diagnóstico Forense dos 4 Gargalos Críticos do Modelo Legado

O diagnóstico da arquitetura anterior revelou 4 causas-raiz estruturais que inviabilizavam a produção contínua em escala:

| Sintoma de Falha | Causa-Raiz Arquitetural | Impacto no Pipeline |
|---|---|---|
| **1. Queda de Frames (Frame Drops)** | Python GIL + OpenCV CPU `VideoWriter` no mesmo processo com sleep arbitrário. | Vídeo engasgado (18-24 FPS instáveis), perda de fluidez nos candles rápidos de 5 segundos. |
| **2. Descompasso Temporal (Telemetry Drift)** | Uso de `time.time()` relativo sem amostragem física do fluxo de frames. | Zooms dinâmicos e SFX na Etapa 3 ocorrem 200ms a 400ms fora do momento do clique. |
| **3. Quebra de Layout (UI Collapse)** | Forçar a janela em proporção 9:16 (ex: 607x1080 ou 1080x1920) ativa responsive layout. | Menus laterais retraem, botões Call/Put são empilhados ou ocultados, quebrando coordenadas. |
| **4. Falso Positivo (Sem Portão de QA)** | Gravação sem verificação pós-execução (gravação cega). | Takes vazios, com ordens rejeitadas ou streams corrompidos avançam e gastam recursos nas etapas seguintes. |

---

## 3. Arquitetura Redesenhada — Solução Integral dos 4 Gargalos

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   PIPELINE ARQUITETURAL REDESENHADO (ETAPA 1)                    │
└──────────────────────────────────────────────────────────────────────────────────┘

 [1. TELA NATIVA IQ OPTION] ── (1920x1080 Imutável @ Full Screen)
             │
             ├──► [PRODUTOR: SCREEN GRABBER THREAD] (mss ultra-otimizado)
             │          │ (Incrementa atomic_frame_index)
             │          ▼
             │    [BOUNDED FRAME QUEUE] (Buffer circular em RAM, maxsize=120)
             │          │
             │          ▼
             │    [CONSUMIDOR: STREAMER THREAD] (Pipe binário direto)
             │          │
             │          ▼
             │    [SUBPROCESSO FFMPEG EXTERNO] (C++ multithread, fora do Python GIL)
             │          │
             │          ├── Auto-Detecção de Hardware:
             │          │   ├── 1. NVIDIA: h264_nvenc (-preset p4 -tune ull -b:v 18M)
             │          │   ├── 2. Intel/AMD HW: h264_mf (-b:v 18M) / h264_qsv
             │          │   └── 3. CPU Baseline: libx264 (-preset ultrafast -crf 18)
             │          ▼
             │    [STAGING VIDEO FILE] (staging/take_xyz/video_master.mp4 @ 60.0 FPS)
             │
 [2. AGENTE AUTÔMATO]
             │ (Dispara ações calibradas: Candles 5s, Bollinger, Call/Put)
             │
             ├──► [MOTOR DE TELEMETRIA ATÔMICA]
             │          │ Consulta atomic_frame_index + time.perf_counter()
             │          ▼
             │    [STAGING TELEMETRY] (staging/take_xyz/telemetry.json)
             │
 [3. PORTÃO DE QA PRÉ-COMMIT]
             │
             ├──► 1. Frame Drop Check (< 0.5% erro de quadros)
             ├──► 2. FFprobe Stream Integrity (Validação do container MP4)
             ├──► 3. UI Confirmation Anchor (Verificação de pixel da ordem aberta)
             └──► 4. JSON Schema Contract v1.0
                         │
                         ├── [SUCESSO] ──► Move para: raw_recordings/take_xyz/
                         └── [FALHA]   ──► Move para: quarantine/take_xyz/ + error_report.json
```

---

### Solução 1: Pipeline Desacoplado Produtor-Consumidor com FFmpeg Assíncrono

Para sustentar **60.0 FPS cravados sem engasgos**:
1. **Thread Produtora (Screen Grabber):**
   - Captura a tela usando `mss` otimizado em loop de alta frequência.
   - Atualiza atomicamente a variável `atomic_frame_index`.
   - Deposita os buffers de imagem em uma fila delimitada (`queue.Queue(maxsize=120)`).
2. **Thread Consumidora (FFmpeg Pipe):**
   - Drena os frames da fila e escreve sem conversões desnecessárias diretamente no `stdin` de um processo FFmpeg dedicado.
   - Caso a thread principal de automação execute um clique ou espere um seletor, o buffer circular absorve o pico sem derrubar a taxa de gravação.
3. **Seletor Adaptativo de Aceleração por Hardware:**
   O motor testa automaticamente os codecs do sistema:
   - Se GPU NVIDIA dedicada: usa `h264_nvenc`.
   - Se Intel HD Graphics / AMD no Windows: usa `h264_mf` (MediaFoundation Hardware API) ou `h264_qsv`.
   - Fallback universal: `libx264 -preset ultrafast -tune zerolatency` no subprocesso C++ do FFmpeg, mantendo o processo Python livre da carga pesada de compressão.

---

### Solução 2: Motor de Telemetria com Dual-Indexação Atômica

O sincronismo entre vídeo e ações atinge precisão cirúrgica através da amarração de cada evento ao índice do frame físico:

- Ao disparar um evento (ex: `SNIPER_TRIGGER_CALL`):
  1. O automador lê o contador atômico: `frame_index = recorder.get_current_frame()`.
  2. Registra o timestamp de precisão: `time_ms = (time.perf_counter() - start_time) * 1000`.
  3. Registra as coordenadas absolutas e a Região de Interesse (ROI).
- **Consumo na Etapa 3 (Remotion / Edição):**
  O editor não precisa adivinhar segundos fracionados. Ele utiliza o índice do frame como referência absoluta no timeline da composição:
  `frame_trigger = telemetry['actions']['SNIPER_TRIGGER_CALL']['frame_index']`.
  **Deriva temporal resultante: 0.0 milissegundos.**

---

### Solução 3: Viewport Imutável 1920x1080 com ROI Dinâmico 9:16

Para evitar o colapso responsivo da interface web da IQ Option:
1. O ambiente operacional permanece fixo em **1920x1080 Full HD Landscape**.
2. Todas as coordenadas do arquivo `config/iqoption_coords.json` são baseadas nesta matriz imutável:
   - Painel esquerdo (Velas, Período 5s, Indicadores): `X: 28-115, Y: 775-935`
   - Área central (Gráfico de Candlesticks): `X: 960, Y: 540`
   - Painel direito (Ordem Call verde, Put vermelha): `X: 1835, Y: 515-625`
3. **Estratégia de Enquadramento 9:16:**
   - O vídeo mestre é capturado em 1080p nativo a 60 FPS com pureza máxima.
   - A telemetria fornece as caixas de enquadramento vertical (**ROIs 9:16**) calibradas:
     - `setup_view`: `X=0, Y=0, W=608, H=1080` (Menu de configuração e velas).
     - `action_view`: `X=656, Y=0, W=608, H=1080` (Ação dos candles em tempo real).
     - `trigger_view`: `X=1312, Y=0, W=608, H=1080` (Botão de disparo sniper e painel de payout).
   - Isso permite ao Remotion realizar efeitos cinematográficos de câmera dinâmica (pan & scan suave) mantendo nitidez cristalina.

---

### Solução 4: Portão de QA Pré-Commit (Automated Pre-Commit QA Gate)

Todo take gravado passa por 4 verificações obrigatórias antes de ser homologado em `raw_recordings/`:

1. **Validação de Taxa de Quadros (Frame Drop Check):**
   - Calcula a diferença entre quadros gravados e o tempo transcorrido:
     $$\Delta = |TotalFrames - (Duração \times 60.0)|$$
   - Se $\Delta > 2$ frames (tolerância < 0.5%), o take é marcado como defeituoso.
2. **Validação de Integridade do Vídeo (FFprobe Check):**
   - Executa `ffprobe -v error -show_entries format=duration,probe_score` para garantir que o container MP4 não possui pacotes corrompidos ou problemas de cabeçalho.
3. **Validação de Confirmação da Operação (UI Pixel Anchor Check):**
   - Inspeciona os pixels da área do painel de operações abertas para atestar que a ordem foi computada pela corretora.
4. **Validação de Contrato do JSON de Telemetria:**
   - Garante a presença dos campos obrigatórios do Schema v1.0.

Se todos os testes passarem, o take é promovido de `staging/` para `raw_recordings/{take_id}/`.  
Se algum teste falhar, o take é movido para `quarantine/{take_id}/` com o relatório `error_report.json`.

---

## 4. Contrato Normativo de Dados: Schema JSON de Telemetria v1.0

Estrutura formal persistida em cada take aprovado (`telemetry.json`):

```json
{
  "schema_version": "1.0",
  "session": {
    "take_id": "take_20261007_001",
    "channel": "El Cazador del Wins",
    "platform": "IQ Option",
    "asset_pair": "EUR/USD-OTC",
    "timeframe": "5s",
    "expiry_seconds": 60,
    "target_fps": 60.0,
    "native_resolution": "1920x1080",
    "created_at": "2026-10-07T00:15:30.120Z",
    "duration_seconds": 28.50,
    "total_frames": 1710
  },
  "qa_status": {
    "verified": true,
    "dropped_frames": 0,
    "drop_rate_percent": 0.0,
    "ffprobe_valid": true,
    "order_confirmed": true
  },
  "rois_9_16": {
    "setup_view": { "x": 0, "y": 0, "width": 608, "height": 1080 },
    "action_view": { "x": 656, "y": 0, "width": 608, "height": 1080 },
    "trigger_view": { "x": 1312, "y": 0, "width": 608, "height": 1080 }
  },
  "actions": [
    {
      "step_id": 1,
      "action_name": "SELECT_CHART_TYPE_CANDLES",
      "frame_index": 72,
      "timestamp_ms": 1200,
      "duration_ms": 400,
      "mouse_x": 115,
      "mouse_y": 775,
      "roi_target": "setup_view"
    },
    {
      "step_id": 2,
      "action_name": "SELECT_TIMEFRAME_5S",
      "frame_index": 168,
      "timestamp_ms": 2800,
      "duration_ms": 350,
      "mouse_x": 115,
      "mouse_y": 830,
      "roi_target": "setup_view"
    },
    {
      "step_id": 3,
      "action_name": "SNIPER_TRIGGER_CALL",
      "frame_index": 620,
      "timestamp_ms": 10333,
      "duration_ms": 150,
      "mouse_x": 1835,
      "mouse_y": 515,
      "roi_target": "trigger_view",
      "metadata": {
        "direction": "CALL",
        "payout_pct": 89
      }
    },
    {
      "step_id": 4,
      "action_name": "WIN_CONFIRMATION",
      "frame_index": 1550,
      "timestamp_ms": 25833,
      "duration_ms": 500,
      "mouse_x": 1835,
      "mouse_y": 450,
      "roi_target": "action_view",
      "metadata": {
        "result": "WIN",
        "profit_usd": 89.0
      }
    }
  ]
}
```

---

## 5. Estrutura de Diretórios Padronizada

```
D:\cazador - videos curtos\
├── ARQUITETURA_ETAPA_1.md             # Documento normativo mestre de arquitetura
├── README.md                          # Guia operacional de uso rápido
├── config/
│   ├── iqoption_coords.json           # Matriz calibrada de coordenadas 1080p
│   └── recorder_config.json          # Parâmetros de codecs, buffer e FPS
├── skills/
│   └── iqoption-screen-recorder/
│       ├── SKILL.md                   # Skill normativa para agentes autônomos
│       └── scripts/
│           └── run_skill.py           # Adaptador de execução de tarefas
├── scripts/
│   ├── screen_recorder.py             # Engine 60 FPS multithread com FFmpeg Pipe
│   ├── qa_validator.py                # Validador de integridade e Portão de QA
│   └── test_calibration.py            # Script utilitário para checagem visual de mira
├── staging/                           # Buffer transitório de gravação
├── raw_recordings/                    # Takes 100% aprovados prontos para edição
│   └── take_YYYYMMDD_NNN/
│       ├── video_master.mp4           # Vídeo Full HD 60.0 FPS sem perda de frames
│       ├── telemetry.json             # Telemetria com índice de frames exato
│       └── qa_report.json             # Certificado do portão de validação
├── quarantine/                        # Takes reprovados com relatório de erro
├── assets/
│   └── sfx/                           # Efeitos sonoros para o Remotion
└── output_shorts/                     # Destino final após Etapas 2 e 3
```

---

## 6. Procedimento de Operação e Comandos de Execução

### 1. Teste de Calibração Visual (Pré-Voo)
```powershell
python "D:\cazador - videos curtos\scripts\test_calibration.py"
```

### 2. Disparo de Gravação Automatizada de Take
```powershell
python "D:\cazador - videos curtos\scripts\screen_recorder.py" --duration 28 --action-set sniper_5s
```

### 3. Validação Manual de QA em um Take Existente
```powershell
python "D:\cazador - videos curtos\scripts\qa_validator.py" --take-dir "D:\cazador - videos curtos\staging\take_exemplo"
```

---

## 7. Critérios de Aceite para Etapas 2 e 3

O orquestrador geral do canal (*El Jefe*) e os editores da Etapa 3 (Remotion) somente consumirão diretórios contidos em `raw_recordings/` que apresentem:
1. `qa_report.json` com status `"PASSED"`.
2. Taxa de quadros comprovada via FFprobe de exatamente `60.00 fps` (ou com desvio inferior a 0.2 fps).
3. `telemetry.json` contendo no mínimo os eventos de `SETUP`, `SNIPER_TRIGGER` e `CONFIRMATION`.
4. Ausência de artefatos de compressão ou congelamento de tela.

*Documento normativo aprovado e arquivado para o pipeline automatizado El Cazador del Wins.*
