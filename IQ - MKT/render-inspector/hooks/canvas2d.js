(() => {
  const rules = __VISUAL_EDITS__;
  const installed = new WeakSet();
  globalThis.__riInstall2D = (ctx, canvas) => {
    const R = globalThis.__renderInspector;
    if (!R || installed.has(ctx)) return;
    installed.add(ctx);
    const canvasId = R.id("canvas", canvas);
    const contextMeta=R.contexts?.get(R.id("context",ctx));if(contextMeta)contextMeta.canvas2dHook=true;
    const rule = Array.isArray(rules) ? rules.find(item => item?.enabled && item.canvas2d && (!item.canvasId || item.canvasId === canvas.id)) : null;
    const remap = rule?.canvas2d;
    const trace = globalThis.__riFlickerTrace;
    const sameColor = (left, right) => String(left).replace(/\s+/g,'').toLowerCase() === String(right).replace(/\s+/g,'').toLowerCase();
    const render = (api, original, self, args, styleProperty=null) => {
      const source = styleProperty && remap?.sourceColor;
      const target = styleProperty && remap?.targetColor;
      const matched = Boolean(source && target && sameColor(self[styleProperty], source));
      const override = trace?.begin('OUR_OVERRIDE',{renderer:'Canvas2D',api,canvasId,matched});
      const previous = styleProperty ? self[styleProperty] : null;
      if(matched) self[styleProperty] = target;
      trace?.end('OUR_OVERRIDE',override,{renderer:'Canvas2D',api,canvasId,changed:matched});
      const draw = trace?.begin('CANVAS_DRAW',{api,canvasId,incorrectStateVisible:matched&&!target});
      try { return original.apply(self,args); }
      finally {
        trace?.end('CANVAS_DRAW',draw,{api,canvasId,incorrectStateVisible:false});
        if(matched) self[styleProperty] = previous;
      }
    };
    for (const api of ["fillText", "strokeText"]) {
      const original = ctx[api];
      if (typeof original !== "function") continue;
      ctx[api] = function(text, x, y, maxWidth) {
        R.safe(api, () => {
          const metrics = this.measureText(String(text));
          const t = this.getTransform();
          const left = x - (metrics.actualBoundingBoxLeft || 0);
          const right = x + (metrics.actualBoundingBoxRight || metrics.width || 0);
          const top = y - (metrics.actualBoundingBoxAscent || parseFloat(this.font) || 10);
          const bottom = y + (metrics.actualBoundingBoxDescent || 0);
          const point = (px, py) => ({x: t.a*px + t.c*py + t.e, y: t.b*px + t.d*py + t.f});
          R.emit("CANVAS2D_TEXT", {
            canvasId, api, text: String(text), x, y, maxWidth: maxWidth ?? null,
            font: this.font, fillStyle: String(this.fillStyle), strokeStyle: String(this.strokeStyle),
            globalAlpha: this.globalAlpha, textAlign: this.textAlign,
            textBaseline: this.textBaseline, direction: this.direction,
            transform: {a:t.a,b:t.b,c:t.c,d:t.d,e:t.e,f:t.f},
            bbox: [point(left,top), point(right,top), point(right,bottom), point(left,bottom)],
            stack: R.level === "deep" ? new Error().stack : null
          });
        });
        return render(api, original, this, Array.from(arguments), api === 'fillText' ? 'fillStyle' : 'strokeStyle');
      };
    }
    for (const [api,style] of [["fillRect","fillStyle"],["strokeRect","strokeStyle"],["fill","fillStyle"],["stroke","strokeStyle"]]) {
      const original=ctx[api];if(typeof original!=="function")continue;
      ctx[api]=function(...args){return render(api,original,this,args,style);};
    }
    const drawImage = ctx.drawImage;
    if (typeof drawImage === "function") ctx.drawImage = function(...args) {
      R.safe("drawImage", () => R.emit("CANVAS2D_IMAGE", {
        canvasId, args: args.slice(1).map(v => Number.isFinite(v) ? v : String(v))
      }));
      return render('drawImage',drawImage,this,args);
    };
    R.emit("CANVAS2D_HOOK_INSTALLED", {canvasId});
  };
})();
