# Architecture

`cli` compõe servidor, navegador próprio, transporte CDP, gerenciador de targets, instrumentação,
coordenador, SQLite e artefatos. O `EventBus` desacopla eventos CDP da UI e da persistência. O estado
da análise é explícito em `state.py`; erros não são convertidos em sucesso.

