# Correlation

A ordem é DOM/SVG/Shadow, Canvas2D e WebGL. DOM concreto encerra a busca. Canvas2D exige interseção
geométrica demonstrável. WebGL usa atividade temporal e estado como candidato, sem alegar posse do
pixel. Confirmação de WebGL específico exige diff/test color ou isolamento, ainda não habilitados em
páginas reais.

