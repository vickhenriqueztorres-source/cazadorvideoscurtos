# Instrumentation

`Runtime.addBinding(__renderInspectorEmit)` transporta lotes JSON ao Python. Os wrappers chamam o
método original com o mesmo `this` e argumentos; erros do inspetor viram `HOOK_ERROR`. A criação do
contexto é observada envolvendo a chamada original de `getContext`, sem sondagem ativa.

