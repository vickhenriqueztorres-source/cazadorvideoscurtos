(() => {
  const R = globalThis.__renderInspector;
  if (!R || typeof document === "undefined" || globalThis.__riSelectorCleanup) return;
  const overlay = document.createElement("div");
  Object.assign(overlay.style, {position:"fixed",pointerEvents:"none",zIndex:"2147483647",border:"2px solid #54d6ff",boxShadow:"0 0 0 1px rgba(0,0,0,.8),0 0 16px rgba(84,214,255,.7)",background:"rgba(84,214,255,.10)",display:"none"});
  const label = document.createElement("div");
  Object.assign(label.style, {position:"fixed",pointerEvents:"none",zIndex:"2147483647",padding:"4px 7px",borderRadius:"4px",background:"#071014",color:"#b8efff",font:"12px/1.2 Consolas,monospace",display:"none"});
  document.documentElement.appendChild(overlay);
  document.documentElement.appendChild(label);
  const previousCursor = document.documentElement.style.cursor;
  document.documentElement.style.cursor = "crosshair";
  const describe = el => {
    const style = getComputedStyle(el), before=getComputedStyle(el,"::before"), after=getComputedStyle(el,"::after");
    const root=el.getRootNode();
    const rect=el.getBoundingClientRect();
    return {tag:el.tagName?.toLowerCase()||"",id:el.id||"",classes:[...el.classList||[]],text:(el.textContent||"").trim().slice(0,300),rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},canvasId:el instanceof HTMLCanvasElement?R.id("canvas",el):null,canvasWidth:el.width??null,canvasHeight:el.height??null,
      renderer:el instanceof SVGElement?"SVG":(root instanceof ShadowRoot?"SHADOW_DOM":"DOM"),
      shadowMode:root instanceof ShadowRoot?root.mode:null,color:style.color,backgroundColor:style.backgroundColor,font:style.font,
      before:{content:before.content,color:before.color,font:before.font,display:before.display},after:{content:after.content,color:after.color,font:after.font,display:after.display}};
  };
  const move = event => { const el=document.elementFromPoint(event.clientX,event.clientY); if(!el)return; const b=el.getBoundingClientRect(); const pointTarget=el instanceof HTMLCanvasElement||el instanceof HTMLIFrameElement||el===document.body||el===document.documentElement; const size=32; const left=pointTarget?Math.max(0,Math.min(innerWidth-size,event.clientX-size/2)):b.left; const top=pointTarget?Math.max(0,Math.min(innerHeight-size,event.clientY-size/2)):b.top; const width=pointTarget?size:b.width; const height=pointTarget?size:b.height; Object.assign(overlay.style,{display:"block",left:`${left}px`,top:`${top}px`,width:`${width}px`,height:`${height}px`,borderRadius:pointTarget?"50%":"2px"}); label.textContent=pointTarget?`PONTO ${Math.round(event.clientX)},${Math.round(event.clientY)} · ${el.tagName.toLowerCase()}${el.id?`#${el.id}`:""}`:`${el.tagName.toLowerCase()}${el.id?`#${el.id}`:""}`; Object.assign(label.style,{display:"block",left:`${Math.min(innerWidth-240,left)}px`,top:`${Math.max(0,top-26)}px`}); };
  const cleanup = () => { removeEventListener("mousemove",move,true); removeEventListener("click",click,true); overlay.remove(); label.remove(); document.documentElement.style.cursor=previousCursor; delete globalThis.__riSelectorCleanup; };
  const click = event => { event.preventDefault(); event.stopImmediatePropagation(); const elements=document.elementsFromPoint(event.clientX,event.clientY).filter(el=>el!==overlay&&el!==label).slice(0,12); R.captureRecentDraws?.(); R.emit("TARGET_SELECTED",{clientX:event.clientX,clientY:event.clientY,pageX:event.pageX,pageY:event.pageY,screenX:event.screenX,screenY:event.screenY,devicePixelRatio:devicePixelRatio,viewportWidth:innerWidth,viewportHeight:innerHeight,scrollX,scrollY,frameUrl:location.href,targetRegion:{x:Math.max(0,event.clientX-16),y:Math.max(0,event.clientY-16),width:32,height:32},elements:elements.map(describe)}); R.flush(); cleanup(); };
  addEventListener("mousemove",move,true); addEventListener("click",click,true); globalThis.__riSelectorCleanup=cleanup;
  R.emit("TARGET_SELECTION_ARMED", {frameUrl:location.href}); R.flush();
})();
