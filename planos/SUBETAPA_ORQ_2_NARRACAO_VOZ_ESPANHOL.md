# SUBETAPA 2: GERAÇÃO DA NARRAÇÃO // BÍBLIA DO CAZADOR (IQ OPTION ES-419)
**Agente Responsável:** `GuionistaVozAgent`  
**Arquivo:** `agents/guionista_voz_agent.py`  
**Status:** ✅ Homologado e Alinhado com a Bíblia Oficial do Personagem  

---

## 1. Arquétipo e Persona do Personagem

```
================================================================================
ARQUÉTIPO:       O Sniper dos Mercados / O Predador da IQ Option
PLATAFORMA:      IQ Option (Reconhecimento visual imediato na LATAM)
CAMPO DE CAÇA:   Velas de M1, M5, Fluxo de Pavio, Rejeição de Taxa e OTC
INIMIGO:         O amador que opera IQ Option como se fosse cassino
VOZ NEURAL:      es-MX-JorgeNeural (Grave -2Hz, Cadência -3%, Neutro es-419)
================================================================================
```

---

## 2. O Algoritmo Mental de 5 Etapas do Cazador

1. **Passo 1: Onde tem sangue na tela hoje? (A Ferida Aberta):**
   - Ataca os erros clássicos: Digital vs Binárias (perder no empate), Velas de 5 segundos (ruleta de dopamina), OTC (achar que é manipulado), 50 indicadores coloridos ("árvore de natal").
2. **Passo 2: O soco no polegar (00s - 03s):**
   - Choque visual e técnico em menos de 1 segundo para travar o scroll no celular.
3. **Passo 3: Desmascarar a ilusão dos amadores (03s - 15s):**
   - Desmonta a mentalidade de cassino e falsas promessas de gurus com tom firme e autoritário.
4. **Passo 4: O tiro do sniper e o mecanismo cirúrgico (15s - 45s):**
   - 1 conceito único de Price Action na IQ Option + janela de silêncio para ouvir o clique seco do mouse.
5. **Passo 5: O WIN, dopamina e o Loop mental invisível (45s - 50s):**
   - Som característico de vitória da IQ Option + saldo subindo em tempo real.
   - **Zero carência e corte seco:** Nada de "inscreva-se", nada de "deixe o like". A frase final fecha sintaticamente com a primeira frase do vídeo, criando um loop infinito (>115% de retenção).

---

## 3. Catálogo dos 5 Roteiros Oficiais da Bíblia

| ID do Tema | Título do Roteiro | Ferida Psicológica Explorada |
|---|---|---|
| `digital_vs_binarias` | O Erro da Opção Digital vs Binária | O novato não entende spread e perde dinheiro no empate na Digital. |
| `velas_5s_roleta` | O Vício da Vela de 5 Segundos | O trader adicto a dopamina operando velas de 5s como se fosse roleta. |
| `otc_algoritmo` | A Leitura do Algoritmo de OTC | O amador que acha que o OTC é cassino e ignora fluxo institucional. |
| `arbol_navidad` | A Armadilha dos 50 Indicadores | A tela poluída com 10 médias, RSI e estocástico que cega a tomada de decisão. |
| `rechazo_pavio_m1` | O Falso Rompimento e o Segundo 31 | Comprar no topo achando que vai romper e tomar loss no último segundo. |

---

## 4. Auditoria Automática do Monólogo Mental (QA Gate do Roteiro)

O `GuionistaVozAgent` executa 4 validações estritas antes de aprovar qualquer roteiro:

1. **`carencia_check` (Zero Carência):** Proíbe expressamente palavras fracas (`por favor`, `suscríbete`, `deja tu like`, `apóyame`, `adiós`).
2. **`duracao_check` (Ritmo & Tempo):** Mantém a contagem entre 45 e 85 palavras em espanhol para respeitar o tempo das pausas do clique.
3. **`ancoragem_iqoption` (Reconhecimento Visual):** Garante a presença de termos chave da plataforma (`IQ Option`, `velas`, `gráfico`, `OTC`, `segundo`, `reloj`).
4. **`loop_invisivel` (Retenção Contínua):** Garante que o fechamento termine em reticências ou conectores sintáticos de loop.

---

## 5. Como Executar

```powershell
# Execução direta com seleção automática de tema via telemetria:
python "D:\cazador - videos curtos\agents\guionista_voz_agent.py" --take-dir "raw_recordings/take_exemplo"

# Forçando um tema específico da Bíblia:
python "D:\cazador - videos curtos\agents\guionista_voz_agent.py" --take-dir "raw_recordings/take_exemplo" --theme digital_vs_binarias
```
