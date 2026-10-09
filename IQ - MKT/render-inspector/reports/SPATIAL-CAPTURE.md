# Captura WebGL e evidência espacial

O clique do seletor solicita uma captura e grava `webgl-frame.json` junto de
`analysis.json` e das capturas de tela. A instrumentação mantém cópias limitadas
dos buffers enviados pela aplicação; cada versão utilizada por um desenho é
preservada. Shaders, uniformes, atributos, índices, viewport, scissor, estados
de rasterização, referências de texturas e pilhas de chamada são registrados.

O clique é convertido de coordenadas CSS para o drawing buffer, incluindo a
origem inferior esquerda usada por `readPixels`. O quadro é coletado entre duas
fronteiras de animação. Se a animação estiver suspensa, um lote temporizado é
coletado e essa diferença é declarada no artefato.

## Identificação espacial

A análise CPU suporta triângulos, triangle strips e triangle fans, índices
inteiros sem sinal e atributos com stride/offset/normalização. São aceitas
atribuições diretas a `gl_Position` com um atributo vec4 ou um construtor vec4
e produtos de uniformes mat4 conhecidos. Matrizes usam a disposição em colunas
do WebGL. Shaders com operações desconhecidas, controle de fluxo, instancing,
clipping ou buffers indisponíveis são registrados como não resolvidos.

Para cada desenho são comparados os valores RGBA do pixel antes e depois da
execução real. Isso detecta contribuição mesmo quando a transformação do shader
não é compreendida. Não prova autoria exclusiva: fundo, texto e sobreposições
podem alterar o mesmo pixel, e um desenho sem diferença pode ainda participar da
imagem. Culling, profundidade, stencil, descarte e textura podem invalidar a
cobertura geométrica como evidência de contribuição.

O painel mostra contagens separadas de cobertura geométrica, mudanças medidas
no pixel e desenhos sem transformação resolvida. O status não é CONFIRMED para
identidade de componentes WebGL.

## Validação

O teste Chromium percorre seletor, clique, captura, análise e persistência. O
canvas é apresentado com escala CSS 2×. Um triângulo indexado com transformação
mat4 cobre o clique e altera seu pixel; outro desenho do mesmo programa é
excluído pelo scissor. O teste verifica os índices, a cor medida, os buffers
persistidos e a ausência de erro GL. Há testes de posição fora do triângulo,
transformação, índices e recusa de shader desconhecido.

Na validação ao vivo de 16/09/2026, a IQ Option estava na tela "Conectando…", com
o canvas inativo e sem desenhos. Isso não valida ainda a geometria da dashboard.
As tentativas vazias estão em `workspace/evidence/spatial-validation/analyses`.

## Limites restantes

- Conteúdo de texturas e reprodução isolada com omissão de chamadas não foram implementados.
- Contextos Offscreen/worker não possuem associação comprovada ao canvas clicado.
- Chamadas por extensões ANGLE de instancing não são interceptadas nesta etapa.
- A captura possui orçamento de memória, chamadas e tempo; cortes são declarados.
- Não há ainda edição de componentes, propriedades de layout ou identificação semântica.

Esta é a base de captura e correlação para a próxima investigação; nenhuma regra
visual é aplicada à plataforma.
