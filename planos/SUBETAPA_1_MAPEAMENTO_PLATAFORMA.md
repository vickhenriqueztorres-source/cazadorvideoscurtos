# SUBETAPA 1: MAPEAMENTO CIRÚRGICO DA PLATAFORMA IQ OPTION
**Agente Responsável:** `Agent-Cartographer`  
**Objetivo:** Identificar, registrar e validar todas as coordenadas de controle da IQ Option (resolução Full HD 1920x1080 nativa e enquadramento ROI 9:16 vertical), com testes de mira, hover e cliques seguros.  
**Status:** Em Validação Prática  

---

## 1. Escopo de Elementos Obrigatórios

Para executar o roteiro sniper do canal com total automação, a plataforma deve ter os seguintes elementos mapeados:

| Elemento | Função Operacional | Posição Padrão (1920x1080) | Posição ROI 9:16 (1080x1920) |
|---|---|---|---|
| **Tipo de Gráfico** | Abrir menu de seleção de gráfico | `(28, 775)` | Barra lateral de configuração |
| **Opção Velas (Candles)** | Selecionar velas japonesas | `(115, 775)` | Menu aberto |
| **Período da Vela** | Abrir seletor de tempo gráfico | `(28, 830)` | Barra lateral |
| **Opção 5 Segundos (5s)** | Ajustar velas para 5 segundos | `(115, 830)` | Seletor de timeframes |
| **Indicadores** | Abrir painel de Bollinger / Médias | `(28, 935)` | Barra lateral |
| **Campo de Valor ($)** | Definir investimento em $1.000 | `(1835, 230)` | Painel superior direito |
| **Campo de Tempo / Expiração** | Definir expiração (30s / 1m) | `(1835, 150)` | Painel superior direito |
| **Botão CALL (Compra)** | Disparo sniper verde (Acima) | `(1835, 515)` | Painel central direito |
| **Botão PUT (Venda)** | Disparo sniper vermelho (Abaixo) | `(1835, 625)` | Painel central direito |
| **Área Central dos Candles** | Foco visual de volatilidade | `(960, 540)` | Centro geométrico do gráfico |
| **Painel de Payout** | Checagem de rendimento ($\ge 85\%$) | `(1835, 430)` | Entre tempo e botões |

---

## 2. Passo a Passo de Execução e Debug

### Passo 1: Captura e Checagem da Resolução Ativa
O script lê os monitores conectados e valida que o monitor primário opera em **1920x1080**.
```powershell
python -c "import pyautogui; print('Resolução:', pyautogui.size())"
```

### Passo 2: Execução do Teste de Mira e Hover Não-Destrutivo
O `Agent-Cartographer` move o cursor com suavidade (`easeInOutQuad`) sobre cada elemento mapeado, pausando 0.5s em cada um para permitir inspeção visual humana e registro de log:
```powershell
python "D:\cazador - videos curtos\scripts\teste_click_debug.py" --mode hover
```

### Passo 3: Teste de Interação Segura com Elementos Neutros
O robô clica em elementos não-financeiros (como o centro do gráfico ou seleção de 5s) para validar o tempo de resposta e o foco da janela:
```powershell
python "D:\cazador - videos curtos\scripts\teste_click_debug.py" --mode safe-click
```

### Passo 4: Persistência e Congelamento do Mapeamento
As coordenadas validadas são gravadas em `D:\cazador - videos curtos\config\iqoption_coords.json`.

---

## 3. Critérios de Aceite para Homologação da Subetapa 1
- [x] Resolução 1920x1080 confirmada.
- [x] Todas as 10 coordenadas essenciais calibradas.
- [x] O cursor atinge exatamente o centro dos botões de CALL e PUT sem errar a área clicável.
- [x] O script `teste_click_debug.py` roda com 0 exceções e gera log de aprovação.
