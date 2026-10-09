# SUBETAPA 3: MONTAGEM PROGRAMÁTICA E PICOS DE DOPAMINA
**Agente Responsável:** `EditorCazadorAgent`  
**Arquivo:** `agents/editor_cazador_agent.py`  
**Objetivo:** Unir vídeo da tela, telemetria, narração e efeitos sonoros para produzir o Short vertical 9:16 (1080x1920) a 60 FPS com zooms dinâmicos sincronizados no clique.

---

## 1. Pacote de Efeitos Sonoros (SFX)
- `sfx_impact.wav`: Impacto grave no segundo 00:01s (Gancho).
- `sfx_mouse_click.wav`: Clique mecânico seco no momento exato do clique (`millisecond_exact`).
- `sfx_heartbeat.wav`: Batimentos cardíacos acelerando entre 16s e 24s.
- `sfx_cash_register.wav`: Som de caixa registradora e moedas no momento do WIN (25s a 28s).

---

## 2. Efeito de Zoom Dinâmico no Clique
- O editor lê `telemetry["click_event"]["second_exact"]` (ex: 13.34s).
- No intervalo `[second_exact - 0.8s, second_exact + 1.2s]`, a câmera aplica zoom de 1.4x focado nas coordenadas do botão.
- No momento do WIN, aplica efeito de shake/punch no popup de lucro.

---

## 3. Passos de Implementação e Debug
1. Sintetizar e disponibilizar os 4 SFX em `assets/sfx/`.
2. Implementar `agents/editor_cazador_agent.py` usando pipeline FFmpeg com `filter_complex`.
3. Renderizar o vídeo completo em `staging/` e validar taxa de 60 FPS.
4. Exportar para `output_shorts/{take_id}_final.mp4`.
