/* Runs in the top document only; no orders, network calls or value changes. */
(() => {
  if (window !== window.top) return;
  const KEY = '__iqVisualLauncher_v1';
  if (window[KEY]) return;
  const ATTR = 'data-iq-visual-launcher-rule';
  const STYLE = 'data-iq-visual-launcher-style';
  const CANVAS_FILTER = 'iq-visual-canvas-filter';
  const CANVAS_SVG = 'data-iq-visual-canvas-filter';
  const canvasContexts = new Map();
  const originalGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(type, ...args) {
    const context = originalGetContext.call(this, type, ...args);
    if (context) canvasContexts.set(this, String(type).toLowerCase());
    return context;
  };
  let config = null;
  const marked = new Set();
  const styles = new Map();
  let diagnostics = {status: 'disabled', elementsChanged: 0, openShadowRoots: 0, warnings: []};

  function restore() {
    for (const node of marked) node.removeAttribute(ATTR);
    marked.clear();
    for (const style of styles.values()) style.remove();
    styles.clear();
    document.querySelector(`[${CANVAS_SVG}]`)?.remove();
  }
  function ensureCanvasFilter(colors) {
    let svg = document.querySelector(`[${CANVAS_SVG}]`);
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute(CANVAS_SVG, '');
      svg.setAttribute('width', '0');
      svg.setAttribute('height', '0');
      svg.style.position = 'absolute';
      svg.style.pointerEvents = 'none';
      (document.body || document.documentElement).appendChild(svg);
    }
    const markup = `<filter id="${CANVAS_FILTER}" color-interpolation-filters="sRGB">
      <feColorMatrix in="SourceGraphic" result="greenRaw" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -1 1.5 -1 0 -0.05"/>
      <feComponentTransfer in="greenRaw" result="greenMask"><feFuncA type="discrete" tableValues="0 0 1 1"/></feComponentTransfer>
      <feColorMatrix in="SourceGraphic" result="redRaw" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  1.5 -1 -1 0 -0.05"/>
      <feComponentTransfer in="redRaw" result="redMask"><feFuncA type="discrete" tableValues="0 0 1 1"/></feComponentTransfer>
      <feFlood flood-color="${colors.profit}" result="greenColor"/><feComposite in="greenColor" in2="greenMask" operator="in" result="greenReplacement"/>
      <feFlood flood-color="${colors.loss}" result="redColor"/><feComposite in="redColor" in2="redMask" operator="in" result="redReplacement"/>
      <feComposite in="SourceGraphic" in2="greenMask" operator="out" result="withoutGreen"/><feComposite in="withoutGreen" in2="redMask" operator="out" result="withoutBoth"/>
      <feMerge><feMergeNode in="withoutBoth"/><feMergeNode in="greenReplacement"/><feMergeNode in="redReplacement"/></feMerge>
    </filter>`;
    const signature = `${colors.profit}|${colors.loss}`;
    if (svg.getAttribute('data-colors') !== signature) {
      svg.innerHTML = markup;
      svg.setAttribute('data-colors', signature);
    }
    return svg;
  }
  function roots() {
    const result = [document];
    for (let i = 0; i < result.length; i++) {
      for (const el of result[i].querySelectorAll('*')) {
        if (el.shadowRoot) result.push(el.shadowRoot);
      }
    }
    return result;
  }
  function scan() {
    if (!config) return;
    if (!document.documentElement) return;
    const domainAuthorized = config.origins.includes(location.origin);
    const routeSupported = config.routes.some(route => route === '/' ? location.pathname === '/' :
      location.pathname === route || location.pathname.startsWith(route + '/'));
    const warnings = [];
    const allRoots = roots();
    const domElements = allRoots.reduce((total, root) => total + root.querySelectorAll('*').length, 0);
    const canvases = [...document.querySelectorAll('canvas')];
    const webglCanvases = canvases.filter(canvas => /webgl/.test(canvasContexts.get(canvas) || '')).length;
    const iframeElements = document.querySelectorAll('iframe').length;
    const navigation = performance.getEntriesByType('navigation')[0];
    const appSurfacePresent = canvases.length > 0 || config.rules.some(rule => {
      try { return allRoots.some(root => root.querySelector(rule.selector)); } catch (_) { return false; }
    });
    const documentLoaded = document.readyState === 'complete';
    const platformSurfaceDetected = routeSupported && appSurfacePresent;
    const renderMode = webglCanvases ? 'webgl' : canvases.length ? 'canvas' : 'dom';
    if (!config.verified) warnings.push('Seletores da IQ Option ainda não validados na plataforma.');
    diagnostics = {status: 'disabled', domainAuthorized, routeSupported,
      themeName: config.themeName, validRules: config.rules.length, totalRules: config.rules.length,
      url: location.href, readyState: document.readyState, documentLoaded, platformSurfaceDetected, renderMode,
      domElements, canvasElements: canvases.length, webglCanvases, iframeElements,
      domContentLoadedMs: Math.round(navigation?.domContentLoadedEventEnd || 0),
      loadEventMs: Math.round(navigation?.loadEventEnd || 0),
      elementsChanged: 0, openShadowRoots: allRoots.length - 1, warnings};
    if (!config.enabled || !domainAuthorized || !routeSupported) {
      restore();
      diagnostics.status = !config.enabled ? 'disabled' : 'incompatible';
      return;
    }
    const next = new Map();
    const css = config.rules.map((rule, i) => `[${ATTR}~="r${i}"] { color: ${rule.color} !important; }`).join('\n');
    const canvasCss = canvases.length ? `canvas { filter: url("#${CANVAS_FILTER}") !important; }` : '';
    let invalid = 0;
    for (const root of allRoots) {
      config.rules.forEach((rule, index) => {
        try {
          for (const node of root.querySelectorAll(rule.selector)) {
            if (node.hasAttribute(ATTR) && !marked.has(node)) continue;
            const tokens = next.get(node) || [];
            tokens.push('r' + index);
            next.set(node, tokens);
          }
        } catch (_) { invalid++; warnings.push('Seletor inválido: ' + rule.selector); }
      });
      let style = styles.get(root);
      if (!style || !style.isConnected) {
        style = document.createElement('style');
        style.setAttribute(STYLE, '');
        (root === document ? document.head || document.documentElement : root).appendChild(style);
        styles.set(root, style);
      }
      const rootCss = root === document ? `${css}\n${canvasCss}` : css;
      if (style.textContent !== rootCss) style.textContent = rootCss;
    }
    if (canvases.length) ensureCanvasFilter(config.canvasColors);
    else document.querySelector(`[${CANVAS_SVG}]`)?.remove();
    for (const node of marked) if (!next.has(node)) { node.removeAttribute(ATTR); marked.delete(node); }
    for (const [node, tokens] of next) {
      const value = tokens.join(' ');
      if (node.getAttribute(ATTR) !== value) node.setAttribute(ATTR, value);
      marked.add(node);
    }
    for (const [root, style] of styles) if (!allRoots.includes(root)) {style.remove(); styles.delete(root);}
    diagnostics.elementsChanged = next.size;
    diagnostics.openShadowRoots = allRoots.length - 1;
    diagnostics.validRules = Math.max(0, config.rules.length - invalid);
    diagnostics.canvasFilterApplied = canvases.length > 0;
    diagnostics.status = next.size || canvases.length ? 'active' : 'incompatible';
    if (!next.size) warnings.push('Nenhum alvo HTML compatível encontrado nesta página.');
    if (!next.size && canvases.length) warnings.push('A interface usa canvas/WebGL; o tema foi aplicado por pós-processamento de cores na superfície gráfica.');
  }
  window[KEY] = {
    configure(value) { config = value; scan(); return diagnostics; },
    snapshot() { scan(); return {...diagnostics, updatedAt: new Date().toISOString()}; },
    restore() { if (config) config.enabled = false; restore(); }
  };
  setInterval(scan, 800);
})();
