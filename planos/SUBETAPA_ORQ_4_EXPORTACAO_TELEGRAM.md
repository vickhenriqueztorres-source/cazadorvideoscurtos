# SUBETAPA 4: EXPORTAÇÃO E FILA DE POSTAGEM VIA TELEGRAM
**Agente Responsável:** `PublicadorTelegramAgent`  
**Arquivo:** `agents/publicador_telegram_agent.py`  
**Objetivo:** Conectar à API de Bot do Telegram e disparar o vídeo renderizado com ficha técnica para aprovação em um clique.

---

## 1. Credenciais e Destino
- **Bot:** `@studiodocsyt_bot`
- **Token:** `8834356238:AAFSTaaMPLOVaHOXRDsox8aVaNnIBbida3g`
- **Chat ID:** `5545230354`

---

## 2. Formato da Mensagem no Telegram
- Envio do vídeo vertical MP4 como vídeo nativo (suporte a reprodução inline no celular e Mac).
- Mensagem formatada:
  ```
  🎯 EL CAZADOR DEL WINS // NOVO SHORT PRONTO!
  📹 Take ID: take_20261007_004644
  📊 Ativo: EUR/USD OTC (5s)
  ⚡ Entrada: CALL ($1.000) @ 13.34s
  💰 Resultado: WIN (+$870)
  ⏱ Duração: 28s | 60 FPS
  ```
