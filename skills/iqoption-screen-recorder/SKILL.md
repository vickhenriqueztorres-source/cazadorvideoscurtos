---
name: iqoption-screen-recorder
description: Gravação de tela cirúrgica 60 FPS com telemetria dual-index (frame + perf_counter) para IQ Option no canal El Cazador del Wins. Use para capturar takes em 1080p nativo com exportação de ROIs 9:16 e validação por QA Gate.
---

# Skill: iqoption-screen-recorder

## Propósito
Esta skill governa a execução técnica da **Etapa 1** da produção de Shorts do canal *El Cazador del Wins*. Ela garante a captura estável da IQ Option em 60.0 FPS reais sem perda de quadros, a sincronização milimétrica de ações de trading com o fluxo de vídeo e a validação automática pré-commit via QA Gate.

## Regras Operacionais Inegociáveis
1. **Ambiente Imutável:** A janela da corretora DEVE estar maximizada em tela cheia na resolução 1920x1080 nativa. Não redimensione a janela para formatos verticais (evita colapso responsivo dos botões Call/Put).
2. **Desacoplamento de Gravação:** Nunca use codificação de vídeo dentro da thread principal do Python. O processo deve invocar o `screen_recorder.py` que canaliza frames em pipe assíncrono para o subprocesso FFmpeg com aceleração de hardware.
3. **Telemetria Dual-Index:** Toda ação automatizada (clique de seleção de velas, ajuste de 5s, entrada sniper de Call ou Put) DEVE registrar tanto o `frame_index` exato quanto o timestamp monotônico em milissegundos.
4. **Passagem Obrigatória pelo QA Gate:** Um take gravado só entra na pasta de produção `raw_recordings/` se for aprovado pelo validador com desvio de frames menor que 0.5% e integridade de container MP4 validada por FFprobe.

## Fluxo de Execução do Agente
1. Verificar se a IQ Option está aberta e visível na tela principal.
2. Iniciar a engine de gravação via CLI:
   ```powershell
   python "D:\cazador - videos curtos\scripts\screen_recorder.py" --duration 30 --action-set sniper_5s
   ```
3. O script gerencia a contagem regressiva, ativa a thread de captura e o pipe FFmpeg.
4. O automador executa os movimentos suaves de mouse e registra as coordenadas e frames de ação.
5. Ao término, o `qa_validator.py` é acionado automaticamente.
6. Se aprovado, o take é catalogado em `raw_recordings/take_YYYYMMDD_NNN/` e disponibilizado para as Etapas 2 e 3 (Edição / Remotion).

## Resolução de Problemas
- **Erro de Codec:** O motor possui fallback automático de NVENC -> MediaFoundation (MF) -> QSV -> libx264 ultrafast.
- **Falha de Coordenadas:** Execute `scripts/test_calibration.py` para revalidar os pontos na interface ativa.
