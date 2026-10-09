# SUBETAPA 2: ESPECIFICAÇÃO NORMATIVA DA SKILL (`SKILL.md`)
**Agente Responsável:** `Agent-SkillArchitect`  
**Localização da Skill:** `D:\cazador - videos curtos\skills\skill-gravacao-tela-iqoption\SKILL.md`  
**Objetivo:** Formalizar as regras de negócio, especificações técnicas, contrato JSON de telemetria e checklist de aceite para a gravação da IQ Option.  
**Status:** Pronto para Implementação Normativa  

---

## 1. Responsabilidades Normativas da Skill

A Skill é a fonte única da verdade para qualquer agente ou automação que execute a gravação.

### Parâmetros Técnicos Obrigatórios:
- **Proporção:** Vertical 9:16 (1080x1920).
- **Taxa de Quadros:** 60 FPS constante cravado (imprescindível para zooms sem desfoque na Etapa 3).
- **Duração do Take:** 28 a 34 segundos.
- **Setup Operacional:**
  - Payout Ativo: $\ge 85\%$ (pares OTC ou Crypto Blitz).
  - Valor Fixo da Operação: $\$1.000$.
  - Tempo de Expiração: 30 segundos (ou 1 minuto conforme o par).

---

## 2. Contrato Estrito de Telemetria (`telemetry.json`)

O arquivo emitido ao final da gravação DEVE seguir rigorosamente esta estrutura para integração com a Etapa 3 (Remotion / FFmpeg):

```json
{
  "take_id": "take_20261007_001",
  "timestamp_start": 0.00,
  "click_event": {
    "second_exact": 12.35,
    "millisecond_exact": 12350,
    "action": "CALL",
    "button_coords": { "x": 1835, "y": 515 },
    "investment_amount": 1000,
    "payout_pct": 87
  },
  "outcome_event": {
    "expiration_second": 27.35,
    "result": "WIN",
    "profit_amount": 870
  },
  "fps": 60,
  "resolution": "1080x1920"
}
```

---

## 3. Checklist de Aceite do Take
- [ ] Sem popups de erro, banners de promoção ou sobreposição de abas.
- [ ] Cursor visível se movendo em direção ao botão entre **00:10s e 00:12s**.
- [ ] Linha tracejada da IQ Option visível no gráfico após a execução do clique.
- [ ] Arquivo MP4 e JSON sincronizados sob o mesmo nome base (`take_XXXX.mp4` e `take_XXXX_telemetry.json`).

---

## 4. Critérios de Aceite para Homologação da Subetapa 2
- [ ] Arquivo `skills/skill-gravacao-tela-iqoption/SKILL.md` criado com YAML frontmatter completo.
- [ ] Validação de integridade do contrato JSON via validador de sintaxe.
- [ ] Skill registrada e compatível com as convenções do Antigravity IDE e Hermes.
