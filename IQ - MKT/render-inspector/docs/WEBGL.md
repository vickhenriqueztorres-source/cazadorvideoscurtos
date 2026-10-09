# WebGL

IDs em `WeakMap` ligam canvas, shaders, programas, texturas, buffers, uniforms e draws. O tracker
guarda programa, unidades de textura, buffers, uniforms, viewport e scissor. Um draw recente é apenas
`PROBABLE` até evidência diferencial confirmar que ele altera o ponto escolhido. WebGPU é detectado,
mas inspeção profunda retorna `UNSUPPORTED_DEEP_INSPECTION`.

