(() => {
  const rules = __VISUAL_EDITS__;
  if (!Array.isArray(rules) || typeof document === 'undefined') return;

  const overlays = new Map();
  const removeOverlay = id => {
    overlays.get(id)?.root?.remove();
    overlays.delete(id);
  };

  const install = rule => {
    const dep = rule.deposit;
    if (!rule.enabled || !dep?.overlay) {
      removeOverlay(rule.id);
      return;
    }
    // O botão pode ser compactado assim que a conta prática for detectada.
    // A captura do bloco de conta chega de forma assíncrona e não deve impedir
    // a remoção do ícone do depósito.
    const practiceDetected = globalThis.__riPracticeDetected === true || globalThis.__riEditorLast?.recoloredVertices > 0;
    if (practiceDetected) globalThis.__riDepositOverlayWasActive = true;
    if (!globalThis.__riDepositOverlayWasActive) {
      removeOverlay(rule.id);
      return;
    }
    const canvas = document.getElementById(rule.canvasId || 'glcanvas');
    if (!(canvas instanceof HTMLCanvasElement) || !canvas.width || !canvas.height) return;

    let state = overlays.get(rule.id);
    if (!state) {
      const root = document.createElement('div');
      root.dataset.renderInspectorOverlay = rule.id;
      Object.assign(root.style, {
        position: 'fixed', inset: '0', pointerEvents: 'none',
        zIndex: '2147483647', contain: 'strict'
      });
      const account = document.createElement('canvas');
      const cover = document.createElement('div');
      const outline = document.createElement('canvas');
      const menuShield = document.createElement('div');
      const menu = document.createElement('canvas');
      const toastGuard = document.createElement('canvas');
      const accountHit = document.createElement('div');
      Object.assign(account.style, {position: 'fixed', pointerEvents: 'none', background: 'transparent'});
      Object.assign(cover.style, {position: 'fixed', pointerEvents: 'none'});
      Object.assign(outline.style, {
        position: 'fixed', pointerEvents: 'none', background: 'transparent'
      });
      Object.assign(menuShield.style, {position:'fixed',pointerEvents:'none',display:'none'});
      Object.assign(menu.style, {position: 'fixed', pointerEvents: 'none', background: 'transparent', display: 'none'});
      Object.assign(toastGuard.style, {position:'fixed',pointerEvents:'none',background:'transparent',display:'none'});
      Object.assign(accountHit.style, {position:'fixed',pointerEvents:'none',background:'transparent',cursor:'pointer'});
      accountHit.addEventListener('click',event=>{
        event.preventDefault();event.stopPropagation();
        const canvas=document.getElementById(rule.canvasId||'glcanvas');if(!(canvas instanceof HTMLCanvasElement))return;
        const box=canvas.getBoundingClientRect(),x=box.right-211*box.width/canvas.width,y=box.top+36*box.height/canvas.height;
        for(const type of ['pointerdown','mousedown','pointerup','mouseup','click'])canvas.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y,button:0,buttons:type.includes('down')?1:0}));
      },true);
      root.append(account, cover, outline, menuShield, menu, toastGuard, accountHit);
      document.documentElement.append(root);
      state = {root, account, cover, outline, menuShield, menu, toastGuard, accountHit};
      overlays.set(rule.id, state);
    }

    const rect = canvas.getBoundingClientRect();
    const sx = rect.width / canvas.width;
    const sy = rect.height / canvas.height;
    const oldLeft = canvas.width - dep.right - dep.sourceWidth;
    const newLeft = canvas.width - dep.right - dep.targetWidth;
    const coverRight = oldLeft + (dep.iconBox?.[2] ?? (newLeft - oldLeft));
    const px = value => `${value}px`;
    const menuRule=rule.accountMenu;
    if(menuRule){
      Object.assign(state.menuShield.style,{
        display:globalThis.__riMenuOpening&&!globalThis.__riMenuPixels?'block':'none',
        left:px(rect.right-menuRule.fromRight*sx),top:px(rect.top+menuRule.top*sy),
        width:px(menuRule.fromRight*sx),height:px((menuRule.bottom-menuRule.top)*sy),
        background:`linear-gradient(to bottom,rgb(37,33,30) 0,rgb(37,33,30) ${71*sy}px,rgb(31,27,24) ${71*sy}px)`
      });
    }

    const pixels = globalThis.__riAccountPixels;
    const accountWidth = pixels ? pixels.width + pixels.dx : 0;
    if (pixels) {
      Object.assign(state.account.style, {
        display: 'block',
        left: px(rect.left + pixels.left * sx),
        top: px(rect.top + pixels.top * sy),
        width: px(accountWidth * sx),
        height: px(pixels.height * sy)
      });
      if (state.account.width !== accountWidth) state.account.width = accountWidth;
      if (state.account.height !== pixels.height) state.account.height = pixels.height;
      const accountContext = state.account.getContext('2d');
      accountContext.fillStyle = `rgb(${dep.backgroundColor.join(',')})`;
      accountContext.fillRect(0, 0, accountWidth, pixels.height);
      accountContext.putImageData(new ImageData(pixels.data, pixels.width, pixels.height), pixels.dx, 0);
    } else {
      state.account.style.display = 'none';
    }
    Object.assign(state.accountHit.style,{
      left:px(rect.left+(canvas.width-430)*sx),top:px(rect.top),width:px(245*sx),height:px(75*sy)
    });

    if(dep.mode==='vertices'){
      state.cover.style.display='none';
      state.outline.style.display='none';
    }else{
      const coverStart = pixels ? pixels.left + accountWidth : oldLeft;
      Object.assign(state.cover.style, {
        display:'block',left: px(rect.left + coverStart * sx),
        top: px(rect.top + (dep.top - 2) * sy),
        width: px(Math.max(0, coverRight - coverStart) * sx),
        height: px((dep.bottom - dep.top + 4) * sy),
        background: `rgb(${dep.backgroundColor.join(',')})`
      });
      Object.assign(state.outline.style, {
        display:'block',left: px(rect.left + newLeft * sx),
        top: px(rect.top + dep.top * sy),
        width: px(dep.targetWidth * sx),
        height: px((dep.bottom - dep.top) * sy)
      });
      const outlineWidth = dep.targetWidth;
      const outlineHeight = dep.bottom - dep.top;
      if (state.outline.width !== outlineWidth) state.outline.width = outlineWidth;
      if (state.outline.height !== outlineHeight) state.outline.height = outlineHeight;
      const context = state.outline.getContext('2d');
      context.clearRect(0, 0, outlineWidth, outlineHeight);
      context.fillStyle = `rgb(${dep.borderColor.join(',')})`;
      context.fillRect(3, 0, outlineWidth - 6, 1);
      context.fillRect(3, outlineHeight - 1, outlineWidth - 6, 1);
      context.fillRect(0, 3, 1, outlineHeight - 6);
      context.fillRect(outlineWidth - 1, 3, 1, outlineHeight - 6);
      const paintCorner = (colors, right, bottom) => {
        const data = context.createImageData(3, 3);
        for (let i = 0; i < 9; i++) {
          const sourceX = right ? 2 - (i % 3) : i % 3;
          const sourceY = i / 3 | 0;
          const color = colors[sourceY * 3 + sourceX];
          data.data.set([...color, 255], i * 4);
        }
        context.putImageData(data, right ? outlineWidth - 3 : 0, bottom ? outlineHeight - 3 : 0);
      };
      paintCorner(dep.topCorner, false, false);
      paintCorner(dep.topCorner, true, false);
      paintCorner(dep.bottomCorner, false, true);
      paintCorner(dep.bottomCorner, true, true);
    }

    const menuPixels = globalThis.__riMenuPixels;
    if (menuPixels) {
      const menuRule = rule.accountMenu;
      const data = new Uint8ClampedArray(menuPixels.data);
      const original = menuPixels.data;
      const pixel = (target, x, y) => (y * menuPixels.width + x) * 4;
      const replaceExact = (x0, y0, x1, y1, from, to) => {
        for (let y=y0;y<y1;y++) for(let x=x0;x<x1;x++) {
          const at=pixel(data,x,y);
          if(data[at]===from[0]&&data[at+1]===from[1]&&data[at+2]===from[2]) data.set(to,at);
        }
      };
      const topBg=[37,33,30],bottomBg=[31,27,24],selectedButton=[40,36,33];
      replaceExact(0,0,menuPixels.width,71,bottomBg,topBg);
      replaceExact(0,71,menuPixels.width,menuPixels.height,topBg,bottomBg);
      replaceExact(196,20,328,56,topBg,selectedButton);
      replaceExact(196,90,328,126,selectedButton,topBg);
      const moveValue = (sourceY,targetY,sourceBg,targetBg,sourceFg,targetFg) => {
        for(let y=0;y<28;y++)for(let x=20;x<180;x++){
          const dst=pixel(data,x,targetY+y);data.set(targetBg,dst);data[dst+3]=255;
        }
        for(let y=0;y<28;y++)for(let x=20;x<180;x++){
          const src=pixel(original,x,sourceY+y),dst=pixel(data,x,targetY+y);
          const dominant=sourceFg[1]>sourceFg[0]?1:0;
          const alpha=Math.max(0,Math.min(1,(original[src+dominant]-sourceBg[dominant])/(sourceFg[dominant]-sourceBg[dominant])));
          if(alpha<0.04)continue;
          for(let c=0;c<3;c++)data[dst+c]=Math.round(targetBg[c]+alpha*(targetFg[c]-targetBg[c]));
          data[dst+3]=255;
        }
      };
      moveValue(102,32,topBg,topBg,menuRule.sourceOrange,menuRule.targetGreen);
      moveValue(32,102,bottomBg,bottomBg,menuRule.targetGreen,menuRule.sourceOrange);
      Object.assign(state.menu.style, {
        display:'block',
        left:px(rect.left+menuPixels.left*sx),top:px(rect.top+menuPixels.top*sy),
        width:px(menuPixels.width*sx),height:px(menuPixels.height*sy)
      });
      if(state.menu.width!==menuPixels.width)state.menu.width=menuPixels.width;
      if(state.menu.height!==menuPixels.height)state.menu.height=menuPixels.height;
      state.menu.getContext('2d').putImageData(new ImageData(data,menuPixels.width,menuPixels.height),0,0);
      globalThis.__riMenuOverlayVisible=true;
    } else {
      state.menu.style.display='none';
      globalThis.__riMenuOverlayVisible=false;
    }
    const toastPixels=globalThis.__riToastGuardPixels;
    if(toastPixels&&performance.now()<(globalThis.__riSuppressBalanceToastUntil||0)){
      Object.assign(state.toastGuard.style,{
        display:'block',left:px(rect.left+toastPixels.left*sx),top:px(rect.top+toastPixels.top*sy),
        width:px(toastPixels.width*sx),height:px(toastPixels.height*sy)
      });
      if(state.toastGuard.width!==toastPixels.width)state.toastGuard.width=toastPixels.width;
      if(state.toastGuard.height!==toastPixels.height)state.toastGuard.height=toastPixels.height;
      state.toastGuard.getContext('2d').putImageData(new ImageData(toastPixels.data,toastPixels.width,toastPixels.height),0,0);
    }else state.toastGuard.style.display='none';
    globalThis.__riDepositOverlay = {
      ruleId: rule.id, oldLeft, newLeft, targetWidth: dep.targetWidth,
      top: dep.top, bottom: dep.bottom, accountShift: rule.accountShift.dx
    };
  };

  const refresh = () => { globalThis.__riOverlayRefreshCount=(globalThis.__riOverlayRefreshCount||0)+1; rules.forEach(install); };
  const start = () => {
    refresh();
    new MutationObserver(refresh).observe(document.documentElement, {childList: true, subtree: true});
    addEventListener('resize', refresh, {passive: true});
    addEventListener('render-inspector-editor-change', refresh);
    addEventListener('render-inspector-menu-change', refresh);
    const hideMenu = () => {
      globalThis.__riMenuRequested=false;
      globalThis.__riMenuOpening=false;
      globalThis.__riMenuCaptureFrozen=false;
      globalThis.__riAccountCaptureFrozen=false;
      globalThis.__riMenuPixels=null;
      globalThis.__riMenuOverlayVisible=false;
      for(const state of overlays.values()){state.menu.style.display='none';state.menuShield.style.display='none';}
    };
    addEventListener('pointerdown',event=>{
      if(!event.isTrusted)return;
      const canvas=document.getElementById('glcanvas');if(!(canvas instanceof HTMLCanvasElement))return;
      const rect=canvas.getBoundingClientRect(),x=(event.clientX-rect.left)*canvas.width/rect.width,y=(event.clientY-rect.top)*canvas.height/rect.height;
      const header=y<75&&x>canvas.width-430&&x<canvas.width-120;
      const menu=y>=75&&y<216&&x>canvas.width-341;
      const accountChoice=menu&&x<canvas.width-149;
      if(header){if(globalThis.__riMenuOverlayVisible||globalThis.__riMenuOpening)hideMenu();else {
        globalThis.__riMenuCaptureFrozen=false;globalThis.__riAccountCaptureFrozen=false;globalThis.__riMenuRequested=true;
        const cache=globalThis.__riMenuCachedPixels;
        globalThis.__riMenuPixels=cache&&cache.canvasWidth===canvas.width&&cache.canvasHeight===canvas.height?cache:null;
        globalThis.__riMenuOpening=!globalThis.__riMenuPixels;
        refresh();
        if(globalThis.__riMenuOpening)setTimeout(()=>{if(globalThis.__riMenuOpening&&!globalThis.__riMenuPixels){globalThis.__riMenuOpening=false;refresh();}},1500);
      }}
      else if(accountChoice&&(globalThis.__riMenuOverlayVisible||globalThis.__riMenuRequested||globalThis.__riMenuOpening)){
        globalThis.__riMenuCachedPixels=null;
        const activeRule=rules.find(item=>item?.enabled&&item.accountMenu);
        const duration=activeRule?.suppressBalanceToast?.durationMs||7000;
        globalThis.__riSuppressBalanceToastUntil=performance.now()+duration;
        for(const delay of [350,700])setTimeout(()=>{
          if(globalThis.__riMenuRequested&&performance.now()-(globalThis.__riMenuCaptureTime||0)>180)hideMenu();
        },delay);
        setTimeout(refresh,duration+50);
      }
      else if(!menu&&(globalThis.__riMenuOverlayVisible||globalThis.__riMenuRequested))hideMenu();
    },true);
    addEventListener('keydown',event=>{if(event.key==='Escape')hideMenu();},true);
  };
  if (document.documentElement) start();
  else addEventListener('DOMContentLoaded', start, {once: true});
})();
