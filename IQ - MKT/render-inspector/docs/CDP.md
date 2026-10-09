# CDP lifecycle

O Chrome inicia em `about:blank` com porta dinâmica e perfil próprio. O controlador lê
`DevToolsActivePort`, conecta ao websocket do browser e ativa discovery/auto-attach com sessões
flattened. A navegação ao alvo ocorre apenas após `Page.addScriptToEvaluateOnNewDocument`.

