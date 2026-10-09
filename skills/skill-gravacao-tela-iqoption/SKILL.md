---
name: skill-gravacao-tela-iqoption
description: Especificação normativa da gravação de tela em 9:16 a 60 FPS com telemetria exata de cliques e expiração para a IQ Option no canal El Cazador del Wins. Define parâmetros técnicos obrigatórios, critérios de setup financeiro, contrato JSON de telemetria e checklist de aceite.
---

# Skill: skill-gravacao-tela-iqoption

> **Documento Normativo de Engenharia & Produção**  
> **Canal:** El Cazador del Wins (@elcazadordelwins)  
> **Destino:** Alimentação automatizada das Etapas 2 e 3 (Montagem / Remotion / FFmpeg)  
> **Status:** Ativo e Normativo  

---

## 1. Responsabilidades Normativas da Skill

Esta Skill define o **que** deve acontecer, os **parâmetros técnicos obrigatórios** e o **formato da telemetria sem acoplamento de código**. Todo agente executor (em especial o `CazadorRecorderAgent`) deve seguir estritamente as diretrizes aqui estabelecidas.

---

## 2. Especificação de Formato Técnico

| Parâmetro | Requisito Obrigatório | Justificativa de Engenharia |
|---|---|---|
| **Proporção** | Vertical 9:16 (1080x1920) | Padrão nativo para YouTube Shorts, Instagram Reels e TikTok. |
| **Taxa de Quadros** | **60 FPS constante** (zero drops) | Necessário para os zooms rápidos e motion blur da Etapa 3 (Remotion) não terem interpolação borrada ou engasgos. |
| **Duração da Tomada** | **28 a 34 segundos** | Janela temporal exata para retenção de 115%+ em loops de Shorts. |
| **Resolução Master** | 1080x1920 (ou 1920x1080 com crop calibrado) | Nitidez máxima em telas mobile retina. |

---

## 3. Critérios de Setup da Sessão

Antes de autorizar a gravação do take, o ambiente e a corretora devem atender:
1. **Paridade / Ativo:** Payout ativo $\ge 85\%$ (preferência para pares OTC ou Crypto Blitz).
2. **Valor Fixado:** Exatamente **$1.000** no campo de investimento.
3. **Tempo de Expiração:** 30 segundos (ou 1 minuto, dependendo do ativo).
4. **Timeframe Gráfico:** Velas de 5 segundos (5s).

---

## 4. Contrato Estrito de Telemetria (`telemetry.json`)

A Skill define o formato exato que a **Etapa 3 (Montagem / Remotion / FFmpeg)** vai ler para posicionar o zoom automático e os efeitos sonoros. O arquivo emitido para cada take (`take_XXXX_telemetry.json`) deve obrigatoriamente validar a seguinte estrutura:

```json
{
  "take_id": "take_20261007_001",
  "timestamp_start": 0.00,
  "click_event": {
    "second_exact": 12.35,
    "millisecond_exact": 12350,
    "action": "CALL",
    "button_coords": { "x": 920, "y": 1450 },
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

### Definição dos Campos do Contrato:
- `take_id`: Identificador único no formato `take_YYYYMMDD_NNN`.
- `timestamp_start`: Início relativo da gravação (0.00s).
- `click_event`:
  - `second_exact`: Segundo exato (com precisão de duas casas) em que o clique ocorreu.
  - `millisecond_exact`: Milissegundo absoluto medido via `time.perf_counter()`.
  - `action`: Direção da ordem (`CALL` ou `PUT`).
  - `button_coords`: Coordenadas no espaço 9:16 `(x, y)` do botão clicado.
  - `investment_amount`: Valor da operação (1000).
  - `payout_pct`: Percentual de rendimento do momento.
- `outcome_event`:
  - `expiration_second`: Segundo exato em que a vela finalizou e a vitória foi computada.
  - `result`: Status do resultado (`WIN`).
  - `profit_amount`: Lucro líquido apurado (ex: 870 para payout de 87%).
- `fps`: Taxa comprovada de 60 quadros por segundo.
- `resolution`: Proporção vertical `1080x1920`.

---

## 5. Checklist de Aceite do Take (Critérios de Homologação)

Para que um take seja homologado e movido para `raw_recordings/`, ele DEVE passar em todos os itens abaixo:

- [ ] **Sem popups de erro ou sobreposição de abas:** A tela deve estar limpa, sem notificações do Windows ou banners promocionais da corretora.
- [ ] **Cursor visível se movendo em direção ao botão entre 00:10s e 00:12s:** O mouse deve executar movimento suave com interpolação `easeInOutQuad`, demonstrando intenção humana e antecipação para o espectador.
- [ ] **Linha tracejada da IQ Option visível no gráfico após o clique:** O gráfico deve exibir a linha horizontal de entrada e a contagem regressiva da ordem aberta.
- [ ] **Arquivo MP4 e JSON sincronizados com o mesmo nome base:** O par de arquivos gerado deve seguir estritamente o padrão:
  - `take_YYYYMMDD_NNN.mp4`
  - `take_YYYYMMDD_NNN_telemetry.json`

---

## 6. Governança e Regras de Segurança
1. **Falha de Timeout:** Se o clique não ocorrer dentro da janela de 10s-13s, a gravação é abortada e descartada para evitar vídeos fora do padrão de retenção.
2. **Rejeição de Ordem:** Se a corretora recusar a entrada (por latência ou volatilidade excessiva), o take é imediatamente encaminhado para a pasta `quarantine/`.
