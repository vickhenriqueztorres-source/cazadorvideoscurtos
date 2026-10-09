# Render Inspector

Ferramenta local para descobrir **quem renderizou** um ponto visual no navegador. Ela inicia um
Chrome/Edge próprio em `about:blank`, conecta diretamente ao Chrome DevTools Protocol (CDP), instala
os hooks e só então navega para a página. Não é uma extensão e não usa Selenium, OCR, IA ou serviço
externo.

## Executar no Windows

```powershell
cd render-inspector
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

O navegador usa o perfil persistente `workspace/browser-profile`. Faça login manualmente na janela
aberta quando necessário. O programa não copia perfil, cookies, senhas ou sessões de outro Chrome.

Opções:

```powershell
python run.py --url https://iqoption.com/traderoom
python run.py --capture deep --debug
```

No painel, clique em **INSPECIONAR ALVO**, volte à página e clique na letra ou gráfico. O clique é
interceptado uma vez. O painel recebe a seleção, o renderer e a evidência; screenshots e resultados
com SHA-256 ficam em `workspace/sessions/<sessão>/analyses/<análise>/`.

## Como funciona

O Python abre uma porta de depuração dinâmica apenas em `127.0.0.1`, descobre o websocket pelo
`DevToolsActivePort` e usa CDP direto. `Target.setAutoAttach` acompanha páginas, iframes e workers.
Páginas recebem `Runtime.addBinding` e `Page.addScriptToEvaluateOnNewDocument`. Workers são pausados
antes do primeiro script, recebem um breakpoint de instrumentação, o hook é avaliado no call frame e
só então continuam.

Os hooks observam a chamada original a `getContext`; nunca chamam `getContext` para sondar a página.
Canvas2D registra texto, cor, fonte, matriz e polígono de `TextMetrics`. WebGL registra IDs estáveis,
shaders, programas, buffers, texturas, uniforms, viewport e draws em lotes. DOM/SVG/Shadow DOM são
analisados antes da camada gráfica. A ausência de evidência resulta em `INCONCLUSIVE`.

## Verificação

```powershell
pytest
python -m ruff check .
python -m mypy src
```

O E2E abre Chromium real e comprova bootstrap antecipado, seletor, screenshot, Canvas2D, iframes
aninhados, worker/OffscreenCanvas e descoberta WebGL. Consulte `reports/` para o estado exato de cada
fase. Test color, leitura de textura e isolamento de draw permanecem experimentais/não habilitados em
páginas reais.

