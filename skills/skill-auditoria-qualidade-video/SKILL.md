---
name: skill-auditoria-qualidade-video
description: Especificação normativa da auditoria automatizada de qualidade pós-produção para vídeos curtos (9:16) no canal El Cazador del Wins. Define a matriz de inspeção de integridade de cabeçalho, HUD inferior, detecção de cortes, congelamento, áudio e validação financeira estrita de vitória (Zero Loss).
---

# Skill: skill-auditoria-qualidade-video

> **Documento Normativo de Controle de Qualidade & Aceite (QA)**  
> **Canal:** El Cazador del Wins (@elcazadordelwins)  
> **Papel Executor:** `AuditorCazadorAgent`  
> **Momento de Execução:** Imediatamente após a Etapa 3 (Montagem) e antes da Etapa 4 (Publicação)  
> **Status:** Ativo e Normativo  

---

## 1. Princípios da Auditoria
Nenhum vídeo pode ser publicado ou enviado ao líder se contiver:
1. Cortes ou truncamentos no cabeçalho superior (logo IQ Option, foto, saldo e botão Deposit).
2. Cortes ou palavras fatiadas no painel inferior (Tier 3).
3. Qualquer segundo de tela preta ou congelamento (freeze).
4. Ausência de áudio sincronizado.
5. Operação perdedora (LOSS) ou ausência de comprovação de lucro financeiro.

---

## 2. Matriz de Auditoria (6 Portões Obrigatórios)

| Portão | Método de Verificação | Critério de Aceite | Ação em caso de Falha |
|---|---|---|---|
| **GATE-1: Container & Streams** | `ffprobe` (JSON) | Resolução `1080x1920`, FPS $\ge 29.97$, duração $50\text{s} \le D \le 65\text{s}$, vídeo `h264`, áudio `aac`. | REJEITAR |
| **GATE-2: Integridade de Fluxo** | OpenCV frame sample (30 frames) | Zero frames pretos ($\text{mean} < 5$), zero congelamento contínuo ($> 1.5\text{s}$). | REJEITAR |
| **GATE-3: Cabeçalho Superior (Tier 1)** | Crop $Y: 0..160$ em 5 instantes ($2\text{s}, 18\text{s}, 26\text{s}, 40\text{s}, 52\text{s}$) | Logo IQ Option visível, saldo legível, botão Deposit sem corte lateral. | REJEITAR |
| **GATE-4: Tier Inferior & HUD (Tier 3)** | Crop $Y: 1200..1550$ em 5 instantes | HUD de saldo preenchido, momento de entrada (CALL/PUT) identificado, sem corte na margem esquerda ($x=0$). | REJEITAR |
| **GATE-5: Regra Financeira Zero-Loss** | Telemetria + Análise de Saldo | `result == "WIN"` e `profit_amount > 0`. | REJEITAR |
| **GATE-6: Integridade do Áudio** | `ffprobe` audio stream | Stream presente, canais $\ge 1$, duração compatível com o vídeo ($\Delta < 1.0\text{s}$). | REJEITAR |

---

## 3. Contrato de Saída (`audit_report.json`)
```json
{
  "take_id": "take_20261008_204109",
  "audited_at": "2026-10-09T00:15:00",
  "overall_verdict": "PASSED",
  "score": 100,
  "gates": {
    "gate_1_container": { "passed": true, "details": "1080x1920 @ 30 FPS" },
    "gate_2_stream_integrity": { "passed": true, "black_frames": 0, "freezes": 0 },
    "gate_3_header_tier1": { "passed": true, "details": "Cabeçalho 100% íntegro sem cortes" },
    "gate_4_bottom_tier3": { "passed": true, "details": "HUD de Saldo e Call/Put visíveis sem cortes" },
    "gate_5_financial_win": { "passed": true, "result": "WIN", "profit": 82 },
    "gate_6_audio_track": { "passed": true, "duration_diff": 0.05 }
  },
  "errors": []
}
```

---

## 4. Política de Autorrecuperação (Self-Healing Loop)
Se `overall_verdict == "FAILED"`:
1. O vídeo é imediatamente isolado em `quarantine/<take_id>/`.
2. O orquestrador central é notificado com a lista de erros (`errors`).
3. O orquestrador reexecuta a esteira (até 3 tentativas) para gerar um novo take que atenda aos 6 portões.
