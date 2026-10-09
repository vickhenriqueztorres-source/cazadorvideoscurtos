# PLANO GERAL DE EXECUÇÃO: AUTOMAÇÃO CIRÚRGICA DE GRAVAÇÃO (ETAPA 1)
**Canal:** El Cazador del Wins (@elcazadordelwins)  
**Formato:** Shorts / Reels / TikTok (Vertical 9:16 @ 60 FPS)  
**Diretório Base:** `D:\cazador - videos curtos`  
**Data:** 07 de Outubro de 2026  
**Status:** Em Execução Progressiva Passo a Passo  

---

## 1. Squad de Agentes Especializados

Para garantir que cada etapa seja implementada, testada e homologada com isolamento de responsabilidades e segurança absoluta, a feature é operada pelo seguinte squad:

| Agente | Arquivo / Papel | Responsabilidade Principal |
|---|---|---|
| **1. Agente Cartógrafo (`Agent-Cartographer`)** | `scripts/mapear_plataforma.py` | Mapeamento pixel-perfect de coordenadas na IQ Option (1080p nativo e ROI 9:16), calibração de mira, testes de hover/clique e validação não-destrutiva de elementos. |
| **2. Agente Arquiteto de Skills (`Agent-SkillArchitect`)** | `skills/skill-gravacao-tela-iqoption/SKILL.md` | Redação da especificação normativa, parâmetros de setup (Payout ≥ 85%, $1.000, 30s), contrato estrito de telemetria JSON e checklist de aceite. |
| **3. Agente Cazador Recorder (`CazadorRecorderAgent`)** | `agents/cazador_recorder_agent.py` | Orquestrador e executor autônomo: gerencia viewport, inicia gravação a 60 FPS constantes, executa a movimentação humana do mouse (10s-12s), dispara o clique sniper, monitora expiração e gera o take sincronizado. |
| **4. Agente Auditor de QA (`Agent-QAGatekeeper`)** | `scripts/qa_validator.py` | Validação pós-gravação: taxa de quadros, integridade do container MP4, presença da telemetria, verificação da linha tracejada e commit/quarentena do take. |

---

## 2. Visão Geral do Pipeline de Execução

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   PIPELINE DE DESENVOLVIMENTO E VALIDAÇÃO                        │
└──────────────────────────────────────────────────────────────────────────────────┘

 [SUBETAPA 1: MAPEAMENTO DA PLATAFORMA]
       │ ──► Mapear elementos: Call, Put, Valor ($1.000), Tempo (30s), Candles 5s, Payout
       │ ──► Teste de mira, hover e clique seguro com debug visual
       │ ──► [VALIDAÇÃO 100% HOMOLOGADA] 
       ▼
 [SUBETAPA 2: A SKILL NORMATIVA (SKILL.md)]
       │ ──► skill-gravacao-tela-iqoption (SKILL.md)
       │ ──► Parâmetros: 9:16 (1080x1920), 60 FPS, 28-34s, $1.000, 30s/1min
       │ ──► Contrato exato de telemetria (click_event + outcome_event)
       │ ──► Checklist de aceite e regras inegociáveis
       │ ──► [VALIDAÇÃO 100% HOMOLOGADA]
       ▼
 [SUBETAPA 3: O AGENTE EXECUTOR (cazador_recorder_agent.py)]
       │ ──► Driver de Viewport / Janela calibrada
       │ ──► Motor de captura 60 FPS dedicado com pipe assíncrono
       │ ──► Automação de mouse suave (10s a 12s) e clique com time.perf_counter()
       │ ──► Geração e emparelhamento de take_XXXX.mp4 + take_XXXX_telemetry.json
       │ ──► [VALIDAÇÃO 100% HOMOLOGADA E TESTADA EM TEMPO REAL]
```

---

## 3. Critério de Passagem Estrito (Zero Tolerância)

Nenhuma subetapa será dada como concluída sem que os seguintes gates sejam validados:
1. **Gate 1 (Mapeamento):** Coordenadas testadas na resolução real, sem colisão de botões e validadas por script de teste com log de acerto.
2. **Gate 2 (Skill):** Contrato normativo documentado, schema JSON verificado e checklist formal de aceite.
3. **Gate 3 (Agente):** Execução prática ponta a ponta gerando o arquivo MP4 e o arquivo JSON com nomes sincronizados e timestamps coincidentes.

---

## 4. Documentos de Detalhamento das Subetapas

Cada subetapa possui seu documento dedicado contendo passo a passo, testes de clique e procedimentos de debug real:
- [SUBETAPA_1_MAPEAMENTO_PLATAFORMA.md](file:///D:/cazador%20-%20videos%20curtos/planos/SUBETAPA_1_MAPEAMENTO_PLATAFORMA.md)
- [SUBETAPA_2_SKILL_GRAVACAO_TELA.md](file:///D:/cazador%20-%20videos%20curtos/planos/SUBETAPA_2_SKILL_GRAVACAO_TELA.md)
- [SUBETAPA_3_AGENTE_CAZADOR_RECORDER.md](file:///D:/cazador%20-%20videos%20curtos/planos/SUBETAPA_3_AGENTE_CAZADOR_RECORDER.md)
