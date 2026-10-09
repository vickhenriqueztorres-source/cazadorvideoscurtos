# Workers

Cada página ativa auto-attach para workers. O worker nasce pausado; o controlador habilita Runtime e
Debugger, cria um breakpoint `beforeScriptExecution`, libera a pausa inicial, avalia os hooks no call
frame e continua. Assim `OffscreenCanvas.getContext` é observado antes do script da aplicação.

