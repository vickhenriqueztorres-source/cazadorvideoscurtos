(() => {
  if (globalThis.__renderInspector) return;
  const R = globalThis.__renderInspector = {
    version: "0.1.0", level: "__CAPTURE_LEVEL__", queue: [], timer: 0,
    canvases: new WeakMap(), contexts: new Map(), serials: Object.create(null), installedAt: performance.now()
  };
  R.id = (kind, object) => {
    const mapName = `${kind}Map`;
    const map = R[mapName] || (R[mapName] = new WeakMap());
    if (!object || (typeof object !== "object" && typeof object !== "function")) return null;
    if (!map.has(object)) {
      R.serials[kind] = (R.serials[kind] || 0) + 1;
      map.set(object, `${kind}_${String(R.serials[kind]).padStart(4, "0")}`);
    }
    return map.get(object);
  };
  R.flush = () => {
    R.timer = 0;
    if (!R.queue.length || typeof globalThis.__renderInspectorEmit !== "function") return;
    const events = R.queue.splice(0, 250);
    try { globalThis.__renderInspectorEmit(JSON.stringify({type: "EVENT_BATCH", events})); }
    catch (_) { R.queue.unshift(...events); }
    if (R.queue.length) R.timer = setTimeout(R.flush, __BATCH_MS__);
  };
  R.emit = (type, payload = {}) => {
    if (R.queue.length >= 20000) {
      R.queue.splice(0, R.queue.length - 19999);
      R.droppedEvents = (R.droppedEvents || 0) + 1;
    }
    R.queue.push({type, payload, jsTimestamp: performance.now()});
    if (!R.timer) R.timer = setTimeout(R.flush, __BATCH_MS__);
  };
  R.captureRecentDraws = () => {
    const cutoff = performance.now() - 2000;
    for (const draw of (R.webglDraws || []).filter(item => item.timestamp >= cutoff))
      R.emit("WEBGL_DRAW", draw);
    R.flush();
  };
  R.safe = (name, fn) => { try { return fn(); } catch (error) {
    R.emit("HOOK_ERROR", {component: name, message: String(error), stack: error?.stack || ""});
  }};
  R.canvasMeta = canvas => {
    const canvasId = R.id("canvas", canvas);
    let rect = null;
    try { if (canvas instanceof HTMLCanvasElement) rect = canvas.getBoundingClientRect().toJSON(); } catch (_) {}
    return {canvasId, elementId:canvas?.id||null, width: canvas.width, height: canvas.height, rect};
  };
  const wrapGetContext = proto => {
    if (!proto?.getContext || proto.getContext.__riWrapped) return;
    const original = proto.getContext;
    function wrapped(...args) {
      const result = original.apply(this, args);
      R.safe("getContext", () => {
        const kind = String(args[0] || "").toLowerCase();
        const meta = {...R.canvasMeta(this), contextType: kind, attributes: args[1] || null};
        const contextId=R.id("context",result);
        if(contextId)R.contexts.set(contextId,{contextId,...meta,scope:typeof document==='undefined'?'worker':'document',runtimeHook:true,canvas2dHook:false,webglHook:false,editorHook:false,ruleId:null});
        R.emit("CANVAS_CONTEXT_CREATED", meta);
        if (kind === "2d" && result) globalThis.__riInstall2D?.(result, this);
        if ((kind === "webgl" || kind === "experimental-webgl" || kind === "webgl2") && result)
          globalThis.__riInstallWebGL?.(result, this, kind);
      });
      return result;
    }
    Object.defineProperty(wrapped, "__riWrapped", {value: true});
    try { Object.defineProperty(wrapped, "name", {value: original.name}); } catch (_) {}
    proto.getContext = wrapped;
  };
  R.safe("HTMLCanvasElement", () => wrapGetContext(globalThis.HTMLCanvasElement?.prototype));
  R.safe("OffscreenCanvas", () => wrapGetContext(globalThis.OffscreenCanvas?.prototype));
  R.emit("HOOK_INSTALLED", {
    scope: typeof document === "undefined" ? "worker" : "document",
    url: globalThis.location?.href || "", webgpu: Boolean(globalThis.navigator?.gpu)
  });
  if (globalThis.navigator?.gpu) R.emit("WEBGPU_DETECTED", {status: "UNSUPPORTED_DEEP_INSPECTION"});
  R.flush();
})();
