(() => {
  const rules = __VISUAL_EDITS__;
  const installed = new WeakSet();
  globalThis.__riInstallWebGLEditor = (gl, canvas) => {
    if (installed.has(gl) || !Array.isArray(rules)) return;
    const rule = rules.find(item => item?.enabled && (!item.canvasId || item.canvasId === canvas.id));
    if (!rule) return;
    installed.add(gl);
    const contextMeta=globalThis.__renderInspector?.contexts?.get(globalThis.__renderInspector?.id?.('context',gl));
    if(contextMeta){contextMeta.editorHook=true;contextMeta.ruleId=rule.id;}
    const features = {
      FLICKER_TRACE: true,
      PRE_RENDER_REMAP: true,
      REFERENCE_SYNC: true,
      ICON_SUPPRESSION: true,
      COLOR_REMAP: true,
      OVERLAY_FALLBACK: false,
      ...(rule.features || {})
    };
    let runtimeEnabled = features.PRE_RENDER_REMAP !== false;
    const trace = globalThis.__riFlickerTrace;
    const traceCanvasId = globalThis.__renderInspector?.id?.('canvas',canvas) || canvas.id || null;
    const traceRecord = (type, payload={}) => {
      if(features.FLICKER_TRACE!==false)trace?.record(type,{ruleId:rule.id,canvasId:traceCanvasId,...payload});
    };
    const traceBegin = (type,payload={}) => features.FLICKER_TRACE!==false?trace?.begin(type,{ruleId:rule.id,canvasId:traceCanvasId,...payload}):null;
    const traceEnd = (type,operationId,payload={}) => {if(operationId!=null&&features.FLICKER_TRACE!==false)trace?.end(type,operationId,{ruleId:rule.id,canvasId:traceCanvasId,...payload});};
    const shadows = new WeakMap(), bound = new Map(), programInfo = new WeakMap();
    const positionTransforms = new WeakMap(), colorTransforms = new WeakMap(), knownBuffers = new Set();
    const originStats = {interceptedWrites:0,interceptedBytes:0};
    let accountCapturePending = false, menuCapturePending = false;
    let lastAccountCaptureAt = 0, lastMenuCaptureAt = 0;
    const native = {
      bufferData: gl.bufferData.bind(gl), bufferSubData: gl.bufferSubData.bind(gl),
      bindBuffer: gl.bindBuffer.bind(gl), drawElements: gl.drawElements.bind(gl)
    };
    const wrap = (name, action) => {
      const previous = gl[name];
      if (typeof previous !== 'function') return;
      gl[name] = function(...args) {
        let called=false,result;
        const guarded=function(...inner){called=true;result=previous.apply(this,inner);return result;};
        try{return action(guarded,this,args);}
        catch(error){
          traceRecord('HOOK_ERROR',{component:`webgl-editor.${name}`,message:String(error),stack:error?.stack||''});
          globalThis.__renderInspector?.emit?.('HOOK_ERROR',{component:`webgl-editor.${name}`,message:String(error),stack:error?.stack||''});
          return called?result:previous.apply(this,args);
        }
      };
    };
    const bytes = (source, offset=0, length) => {
      if (source instanceof ArrayBuffer) return new Uint8Array(source);
      if (!ArrayBuffer.isView(source)) return null;
      const unit=source.BYTES_PER_ELEMENT||1;
      const size=length===undefined||length===0?source.byteLength-offset*unit:length*unit;
      return new Uint8Array(source.buffer,source.byteOffset+offset*unit,size);
    };
    const positionsFor = buffer => {
      let value=positionTransforms.get(buffer);
      if(!value){value=new Map();positionTransforms.set(buffer,value);knownBuffers.add(buffer);}
      return value;
    };
    const colorsFor = buffer => {
      let value=colorTransforms.get(buffer);
      if(!value){value=new Map();colorTransforms.set(buffer,value);knownBuffers.add(buffer);}
      return value;
    };
    const reportOrigin = () => {
      let accountPositions=0,depositPositions=0,depositTextPositions=0,balanceColors=0,depositIconColors=0;
      for(const buffer of knownBuffers){
        for(const value of positionTransforms.get(buffer)?.values()||[]){
          if(value.kind==='account')accountPositions++;else if(value.kind==='deposit-border')depositPositions++;else if(value.kind==='deposit-text')depositTextPositions++;
        }
        for(const value of colorTransforms.get(buffer)?.values()||[]){
          if(value.kind==='balance')balanceColors++;else if(value.kind==='deposit-icon')depositIconColors++;
        }
      }
      globalThis.__riOriginPatches={accountPositions,depositPositions,depositTextPositions,balanceColors,depositIconColors,...originStats};
    };
    const featureAllows = kind => kind==='balance'?features.COLOR_REMAP!==false:kind==='deposit-icon'?features.ICON_SUPPRESSION!==false:features.REFERENCE_SYNC!==false;
    const restoreOriginal = () => {
      for(const buffer of knownBuffers){
        const data=shadows.get(buffer);if(!data)continue;
        const view=new DataView(data.buffer,data.byteOffset,data.byteLength),changed=[];
        for(const [at,transform] of positionTransforms.get(buffer)||[]){
          if(at+4>data.byteLength)continue;
          view.setFloat32(at,transform.original,true);changed.push(at,at+3);
        }
        for(const [at,transform] of colorTransforms.get(buffer)||[]){
          if(!transform.originalColor||at+transform.originalColor.length>data.byteLength)continue;
          data.set(transform.originalColor,at);changed.push(at,at+transform.originalColor.length-1);
        }
        if(!changed.length)continue;
        const current=gl.getParameter(gl.ARRAY_BUFFER_BINDING),start=Math.min(...changed),end=Math.max(...changed)+1;
        if(current!==buffer)native.bindBuffer(gl.ARRAY_BUFFER,buffer);
        native.bufferSubData(gl.ARRAY_BUFFER,start,data.subarray(start,end));
        if(current!==buffer)native.bindBuffer(gl.ARRAY_BUFFER,current);
      }
      traceRecord('PRE_RENDER_REMAP_DISABLED',{restored:true});
    };
    const setEnabled = value => {
      const next=Boolean(value);if(next===runtimeEnabled)return runtimeEnabled;
      if(!next)restoreOriginal();
      runtimeEnabled=next;
      traceRecord(next?'PRE_RENDER_REMAP_ENABLED':'PRE_RENDER_REMAP_DISABLED',{restored:!next});
      return runtimeEnabled;
    };
    globalThis.__riVisualControl={
      enable:()=>setEnabled(true),disable:()=>setEnabled(false),
      setFeature:(name,value)=>{if(Object.hasOwn(features,name))features[name]=Boolean(value);return {...features};},
      state:()=>({enabled:runtimeEnabled,features:{...features},ruleId:rule.id})
    };
    const applySourceTransforms = (buffer,start,source) => {
      const positions=positionTransforms.get(buffer),colors=colorTransforms.get(buffer);
      if(!runtimeEnabled||(!positions?.size&&!colors?.size)||!source.byteLength)return source;
      const output=source.slice(),view=new DataView(output.buffer,output.byteOffset,output.byteLength);
      let changed=false;
      for(const [at,transform] of positions||[]){
        if(!featureAllows(transform.kind))continue;
        const local=at-start;if(local<0||local+4>output.byteLength)continue;
        const original=view.getFloat32(local,true);
        transform.original=original;
        const viewport=gl.getParameter(gl.VIEWPORT),width=Math.max(1,viewport[2]);
        view.setFloat32(local,original+(2*transform.shiftPx/width),true);
        changed=true;
      }
      for(const [at,transform] of colors||[]){
        if(!featureAllows(transform.kind))continue;
        const local=at-start,targetLength=transform.target.length;if(local<0||local+targetLength>output.byteLength)continue;
        transform.originalColor=Array.from(output.subarray(local,local+targetLength));
        if(transform.kind==='balance'){
          const sourceColor=rule.balance.sourceColor,t=rule.balance.tolerance;
          const matches=Math.abs(output[local]-sourceColor[0])<=t&&Math.abs(output[local+1]-sourceColor[1])<=t&&Math.abs(output[local+2]-sourceColor[2])<=t;
          if(!matches)continue;
          globalThis.__riPracticeDetected=true;
        }else if(!globalThis.__riPracticeDetected)continue;
        output.set(transform.target,local);changed=true;
      }
      if(changed){originStats.interceptedWrites++;originStats.interceptedBytes+=output.byteLength;reportOrigin();}
      return changed?output:source;
    };
    wrap('bindBuffer',(fn,self,args)=>{const result=fn.apply(self,args);bound.set(args[0],args[1]);return result;});
    wrap('bufferData',(fn,self,args)=>{traceRecord('ORIGINAL_STATE_UPDATE',{api:'bufferData',byteLength:args[1]?.byteLength??(typeof args[1]==='number'?args[1]:null)});const result=fn.apply(self,args);const b=bound.get(args[0]);if(b){positionTransforms.delete(b);colorTransforms.delete(b);knownBuffers.delete(b);const data=typeof args[1]==='number'?new Uint8Array(args[1]):bytes(args[1],args[3],args[4]);if(data&&data.byteLength<=32*1024*1024)shadows.set(b,data.slice());else shadows.delete(b);}return result;});
    wrap('bufferSubData',(fn,self,args)=>{
      const buffer=bound.get(args[0]),target=shadows.get(buffer),source=bytes(args[2],args[3],args[4]);
      traceRecord('TARGET_STATE_UPDATE',{api:'bufferSubData',byteOffset:args[1],byteLength:source?.byteLength||0});
      const operation=traceBegin('OUR_OVERRIDE',{phase:'bufferSubData'});
      const patched=buffer&&source?applySourceTransforms(buffer,args[1],source):source;
      traceEnd('OUR_OVERRIDE',operation,{phase:'bufferSubData',changed:Boolean(patched&&patched!==source)});
      const result=patched&&patched!==source?fn.call(self,args[0],args[1],patched):fn.apply(self,args);
      if(target&&source&&args[1]+source.byteLength<=target.byteLength){
        target.set(patched||source,args[1]);
      }
      return result;
    });
    const infoFor = program => {
      if(programInfo.has(program))return programInfo.get(program);
      const attributes={};
      for(let i=0;i<gl.getProgramParameter(program,gl.ACTIVE_ATTRIBUTES);i++){
        const info=gl.getActiveAttrib(program,i);attributes[info.name]=gl.getAttribLocation(program,info.name);
      }
      const shaders=(gl.getAttachedShaders(program)||[]).map(s=>gl.getShaderSource(s)||'');
      const supported=/gl_Position\s*=\s*vec4\s*\(\s*a_position\s*\)/.test(shaders.join('\n'));
      const value={supported,position:attributes.a_position,color:attributes.a_color};programInfo.set(program,value);return value;
    };
    const readIndices = (data,type,count,offset) => {
      const format=type===gl.UNSIGNED_BYTE?['B',1]:type===gl.UNSIGNED_SHORT?['H',2]:type===gl.UNSIGNED_INT?['I',4]:null;
      if(!format||offset+count*format[1]>data.byteLength)return null;
      const view=new DataView(data.buffer,data.byteOffset,data.byteLength),out=[];
      for(let i=0;i<count;i++){const at=offset+i*format[1];out.push(format[0]==='B'?view.getUint8(at):format[0]==='H'?view.getUint16(at,true):view.getUint32(at,true));}
      return out;
    };
    const attribute = location => location<0?null:{enabled:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_ENABLED),size:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_SIZE),type:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_TYPE),stride:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_STRIDE),offset:gl.getVertexAttribOffset(location,gl.VERTEX_ATTRIB_ARRAY_POINTER),buffer:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_BUFFER_BINDING)};
    wrap('drawElements',(fn,self,args)=>{
      const drawNative=payload=>{
        const drawOperation=traceBegin('WEBGL_DRAW',{api:'drawElements',...payload});
        const value=fn.apply(self,args);
        traceEnd('WEBGL_DRAW',drawOperation,{api:'drawElements',...payload});
        return value;
      };
      const program=gl.getParameter(gl.CURRENT_PROGRAM),info=program&&infoFor(program);
      if(!info?.supported||args[0]!==gl.TRIANGLES)return drawNative({intercepted:false});
      const pos=attribute(info.position),color=attribute(info.color);
      const vertexBuffer=pos?.buffer,indexBuffer=bound.get(gl.ELEMENT_ARRAY_BUFFER);
      const vertexData=shadows.get(vertexBuffer),indexData=shadows.get(indexBuffer);
      const indices=indexData&&readIndices(indexData,args[2],args[1],args[3]);
      if(!pos?.enabled||pos.type!==gl.FLOAT||pos.size<2||!vertexData||!indices)return drawNative({intercepted:false});
      const overrideOperation=traceBegin('OUR_OVERRIDE',{phase:'drawElements'});
      const stride=pos.stride||pos.size*4,view=new DataView(vertexData.buffer,vertexData.byteOffset,vertexData.byteLength);
      const width=gl.drawingBufferWidth,height=gl.drawingBufferHeight,bal=rule.balance;
      const viewport=gl.getParameter(gl.VIEWPORT),screen=new Map();
      const point=index=>{if(screen.has(index))return screen.get(index);const at=pos.offset+index*stride;if(at+8>vertexData.byteLength)return null;const rawX=view.getFloat32(at,true),rawY=view.getFloat32(at+4,true);const value={index,at,rawX,rawY,x:viewport[0]+(rawX+1)*viewport[2]/2,y:viewport[1]+(rawY+1)*viewport[3]/2};screen.set(index,value);return value;};
      const uniqueIndices=new Set(indices);
      const changed=new Set(),stats={recoloredVertices:0,shiftedVertices:0,depositShiftedVertices:0,depositTextShiftedVertices:0,depositIconVertices:0,menuVertices:0};
      const editByte=(at,value)=>{vertexData[at]=value;changed.add(at);};
      const topY=y=>height-y;
      let numberHash=2166136261,numberVertices=0;
      const hashByte=value=>{numberHash^=value;numberHash=Math.imul(numberHash,16777619)>>>0;};
      for(const index of uniqueIndices){
        const p=point(index);if(!p)continue;
        const positionTransform=positionTransforms.get(vertexBuffer)?.get(p.at);
        const logicalRawX=positionTransform?.original??p.rawX;
        const logicalX=viewport[0]+(logicalRawX+1)*viewport[2]/2;
        if(logicalX<width-bal.regionFromRight[1]||logicalX>width-bal.regionFromRight[0]||p.y<topY(bal.bottom)||p.y>topY(bal.top))continue;
        numberVertices++;hashByte(index&255);hashByte(index>>>8&255);
        const uvStart=Math.min(p.at+12,p.at+stride),uvEnd=Math.min(p.at+stride,vertexData.byteLength);
        for(let at=uvStart;at<uvEnd;at++)hashByte(vertexData[at]);
      }
      if(numberVertices){
        const telemetry=globalThis.__riNumberTelemetry||(globalThis.__riNumberTelemetry={draws:0,changes:0,sources:{},samples:[]});
        telemetry.sources=telemetry.sources||{};telemetry.draws++;
        const sourceKey=`${globalThis.__renderInspector?.id?.('program',program)||'program'}|${globalThis.__renderInspector?.id?.('buffer',vertexBuffer)||'buffer'}|${args[1]}|${args[3]}|${numberVertices}`;
        const source=telemetry.sources[sourceKey]||(telemetry.sources[sourceKey]={draws:0,changes:0,lastHash:null,vertices:numberVertices});source.draws++;
        if(source.lastHash!==numberHash){source.changes++;source.lastHash=numberHash;telemetry.changes++;telemetry.samples.push({timestamp:performance.now(),frameSequence:trace?.frameSequence||0,sourceKey,hash:numberHash,vertices:numberVertices});if(telemetry.samples.length>100)telemetry.samples.shift();}
      }
      for(const index of uniqueIndices){
        const p=point(index);if(!p)continue;
        if(color?.enabled&&color.type===gl.UNSIGNED_BYTE&&color.size>=4){
          const cs=color.stride||color.size,at=color.offset+index*cs;
          const menu=rule.accountMenu,source=bal.sourceColor,t=bal.tolerance;
          const positionTransform=positionTransforms.get(vertexBuffer)?.get(p.at);
          const logicalRawX=positionTransform?.original??p.rawX;
          const logicalX=viewport[0]+(logicalRawX+1)*viewport[2]/2;
          const dep=rule.deposit;
          if(dep?.mode==='vertices'){
            const oldLeft=width-dep.right-dep.sourceWidth,fromTop=height-p.y;
            const inIcon=logicalX>=oldLeft+dep.iconBox[0]&&logicalX<=oldLeft+dep.iconBox[2]&&fromTop>=dep.iconBox[1]&&fromTop<=dep.iconBox[3];
            // The platform emits this icon in more than one green. Its geometry is
            // isolated inside iconBox, so position is the stable identifier; tying
            // suppression to borderColor lets the icon reappear after theme/state
            // updates (for example #51a85d instead of the native border green).
            if(inIcon&&at+4<=vertexData.byteLength&&!colorsFor(vertexBuffer).has(at))colorsFor(vertexBuffer).set(at,{kind:'deposit-icon',target:[0,0,0,0],originalColor:Array.from(vertexData.subarray(at,at+4))});
          }
          if(menu&&at+4<=vertexData.byteLength&&p.x>=width-menu.fromRight-20.5&&p.x<=width+.5&&p.y>=topY(menu.bottom)-.5&&p.y<=topY(menu.top)+.5&&Math.abs(vertexData[at]-source[0])<=t&&Math.abs(vertexData[at+1]-source[1])<=t&&Math.abs(vertexData[at+2]-source[2])<=t)stats.menuVertices++;
          if(at+4<=vertexData.byteLength&&logicalX>=width-bal.regionFromRight[1]&&logicalX<=width-bal.regionFromRight[0]&&p.y>=topY(bal.bottom)&&p.y<=topY(bal.top)){
            if(Math.abs(vertexData[at]-source[0])<=t&&Math.abs(vertexData[at+1]-source[1])<=t&&Math.abs(vertexData[at+2]-source[2])<=t){if(!colorsFor(vertexBuffer).has(at))colorsFor(vertexBuffer).set(at,{kind:'balance',target:bal.targetColor,originalColor:Array.from(vertexData.subarray(at,at+4))});globalThis.__riPracticeDetected=true;stats.recoloredVertices++;}
          }
        }
      }
      for(const [at,transform] of colorTransforms.get(vertexBuffer)||[]){
        if(!runtimeEnabled||!featureAllows(transform.kind))continue;
        if(transform.kind==='deposit-icon'&&!globalThis.__riPracticeDetected)continue;
        for(let channel=0;channel<transform.target.length;channel++)editByte(at+channel,transform.target[channel]);
        if(transform.kind==='deposit-icon')stats.depositIconVertices++;
      }
      const account=rule.accountShift;
      if(account?.mode==='vertices'&&globalThis.__riPracticeDetected){
        globalThis.__riAccountShiftMode='vertices';
        const positions=positionsFor(vertexBuffer);
        const left=width-account.leftFromRight,right=width-account.rightFromRight;
        const accountDx=account.syncWithDeposit&&rule.deposit?rule.deposit.sourceWidth-rule.deposit.targetWidth:account.dx;
        for(const index of uniqueIndices){
          const p=point(index);if(!p)continue;
          let transform=positions.get(p.at);
          if(!transform){
            const inside=p.x>=left&&p.x<=right&&p.y>=topY(account.bottom)&&p.y<=topY(account.top);
            if(!inside)continue;
            transform={kind:'account',original:p.rawX,shiftPx:accountDx};positions.set(p.at,transform);
          }
          if(transform.kind!=='account')continue;
          if(!runtimeEnabled||!featureAllows(transform.kind))continue;
          const desired=transform.original+(2*transform.shiftPx/Math.max(1,viewport[2]));
          if(Math.abs(view.getFloat32(p.at,true)-desired)>1e-7){view.setFloat32(p.at,desired,true);for(let byte=0;byte<4;byte++)changed.add(p.at+byte);stats.shiftedVertices++;}
        }
      }
      const dep=rule.deposit;
      if(dep?.mode==='vertices'&&globalThis.__riPracticeDetected){
        globalThis.__riDepositGeometryMode='vertices';
        const positions=positionsFor(vertexBuffer);
        const oldLeft=width-dep.right-dep.sourceWidth,newLeft=width-dep.right-dep.targetWidth,dx=newLeft-oldLeft;
        for(const index of uniqueIndices){
          const p=point(index);if(!p)continue;
          let transform=positions.get(p.at);
          if(!transform){
            // The native rounded border has an outer and inner left edge eight pixels apart.
            // Move both as one source component; moving only the outer edge deforms the arc.
            const fromTop=height-p.y,leftEdge=p.x>=oldLeft-1&&p.x<=oldLeft+9&&fromTop>=dep.top-1&&fromTop<=dep.bottom+1;
            const inText=Array.isArray(dep.textBox)&&p.x>=oldLeft+dep.textBox[0]&&p.x<=oldLeft+dep.textBox[2]&&fromTop>=dep.textBox[1]&&fromTop<=dep.textBox[3];
            if(leftEdge)transform={kind:'deposit-border',original:p.rawX,shiftPx:dx};
            else if(inText)transform={kind:'deposit-text',original:p.rawX,shiftPx:dep.textDx||0};
            else continue;
            positions.set(p.at,transform);
          }
          if(transform.kind!=='deposit-border'&&transform.kind!=='deposit-text')continue;
          if(!runtimeEnabled||!featureAllows(transform.kind))continue;
          const desired=transform.original+(2*transform.shiftPx/Math.max(1,viewport[2]));
          if(Math.abs(view.getFloat32(p.at,true)-desired)>1e-7){view.setFloat32(p.at,desired,true);for(let byte=0;byte<4;byte++)changed.add(p.at+byte);if(transform.kind==='deposit-border')stats.depositShiftedVertices++;else stats.depositTextShiftedVertices++;}
        }
      }
      reportOrigin();
      let current=null;
      if(changed.size){
        globalThis.__riEditorLast=stats;
        current=bound.get(gl.ARRAY_BUFFER);
        const start=Math.min(...changed),end=Math.max(...changed)+1;if(current!==vertexBuffer)native.bindBuffer(gl.ARRAY_BUFFER,vertexBuffer);native.bufferSubData(gl.ARRAY_BUFFER,start,vertexData.subarray(start,end));
      }
      let incorrectStateVertices=0,motionDeltaPx=0;
      for(const [at,transform] of colorTransforms.get(vertexBuffer)||[]){
        if(transform.kind==='balance'){
          const source=rule.balance.sourceColor,t=rule.balance.tolerance;
          if(Math.abs(vertexData[at]-source[0])<=t&&Math.abs(vertexData[at+1]-source[1])<=t&&Math.abs(vertexData[at+2]-source[2])<=t)incorrectStateVertices++;
        }else if(transform.kind==='deposit-icon'&&vertexData[at+3]!==0)incorrectStateVertices++;
      }
      for(const [at,transform] of positionTransforms.get(vertexBuffer)||[]){
        const desired=transform.original+(2*transform.shiftPx/Math.max(1,viewport[2]));
        const delta=Math.abs(view.getFloat32(at,true)-desired)*viewport[2]/2;
        motionDeltaPx=Math.max(motionDeltaPx,delta);if(delta>.01)incorrectStateVertices++;
      }
      traceEnd('OUR_OVERRIDE',overrideOperation,{phase:'drawElements',changedBytes:changed.size,incorrectStateVertices,motionDeltaPx});
      const result=drawNative({intercepted:true,incorrectStateVertices,motionDeltaPx,changedBytes:changed.size});
      if(changed.size&&current!==vertexBuffer)native.bindBuffer(gl.ARRAY_BUFFER,current);
      const now=performance.now();
      const accountPixels=globalThis.__riAccountPixels;
      const accountSizeMatches=accountPixels&&accountPixels.canvasWidth===width&&accountPixels.canvasHeight===height;
      if(accountPixels&&!accountSizeMatches)globalThis.__riAccountPixels=null;
      if(stats.recoloredVertices&&rule.accountShift?.mode!=='vertices'&&!accountCapturePending&&!globalThis.__riAccountCaptureFrozen&&!accountSizeMatches){
        accountCapturePending=true;
        lastAccountCaptureAt=now;
        const captureStats=globalThis.__riCaptureCounts||(globalThis.__riCaptureCounts={account:0,menu:0});captureStats.account++;
        queueMicrotask(()=>{
          accountCapturePending=false;
          if(globalThis.__riAccountCaptureFrozen)return;
          const account=rule.accountShift,left=Math.max(0,width-account.leftFromRight),right=Math.min(width,width-account.rightFromRight);
          const captureWidth=right-left,captureHeight=account.bottom-account.top,raw=new Uint8Array(captureWidth*captureHeight*4);
          try{
            gl.readPixels(left,height-account.bottom,captureWidth,captureHeight,gl.RGBA,gl.UNSIGNED_BYTE,raw);
            const flipped=new Uint8ClampedArray(raw.length),row=captureWidth*4;
            for(let y=0;y<captureHeight;y++)flipped.set(raw.subarray((captureHeight-1-y)*row,(captureHeight-y)*row),y*row);
            globalThis.__riAccountPixels={left,top:account.top,width:captureWidth,height:captureHeight,dx:account.dx,canvasWidth:width,canvasHeight:height,data:flipped};
            globalThis.dispatchEvent?.(new Event('render-inspector-editor-change'));
          }catch{}
        });
      }
      const menuNeedsCapture=globalThis.__riMenuRequested!==false&&(!globalThis.__riMenuPixels||globalThis.__riMenuOpening);
      if(stats.menuVertices&&rule.accountMenu&&menuNeedsCapture&&!menuCapturePending&&!globalThis.__riMenuCaptureFrozen&&now-lastMenuCaptureAt>=250){
        menuCapturePending=true;
        lastMenuCaptureAt=now;
        const captureStats=globalThis.__riCaptureCounts||(globalThis.__riCaptureCounts={account:0,menu:0});captureStats.menu++;
        queueMicrotask(()=>{
          menuCapturePending=false;
          if(globalThis.__riMenuCaptureFrozen)return;
          const menu=rule.accountMenu,left=Math.max(0,width-menu.fromRight),captureWidth=width-left,captureHeight=menu.bottom-menu.top,raw=new Uint8Array(captureWidth*captureHeight*4);
          try{
            gl.readPixels(left,height-menu.bottom,captureWidth,captureHeight,gl.RGBA,gl.UNSIGNED_BYTE,raw);
            const flipped=new Uint8ClampedArray(raw.length),row=captureWidth*4;
            for(let y=0;y<captureHeight;y++)flipped.set(raw.subarray((captureHeight-1-y)*row,(captureHeight-y)*row),y*row);
            let backgroundPixels=0;
            for(let i=0;i<flipped.length;i+=4){
              const r=flipped[i],g=flipped[i+1],b=flipped[i+2];
              if((Math.abs(r-31)<=2&&Math.abs(g-27)<=2&&Math.abs(b-24)<=2)||(Math.abs(r-37)<=2&&Math.abs(g-33)<=2&&Math.abs(b-30)<=2))backgroundPixels++;
            }
            const colorPixels=(y0,y1,rgb)=>{
              let count=0;
              for(let y=y0;y<Math.min(y1,captureHeight);y++)for(let x=20;x<Math.min(180,captureWidth);x++){
                const at=(y*captureWidth+x)*4;
                if(Math.abs(flipped[at]-rgb[0])<30&&Math.abs(flipped[at+1]-rgb[1])<30&&Math.abs(flipped[at+2]-rgb[2])<30)count++;
              }
              return count;
            };
            const menuVisible=globalThis.__riMenuRequested!==false&&backgroundPixels/(captureWidth*captureHeight)>0.42&&colorPixels(32,60,menu.targetGreen)>30&&colorPixels(102,130,menu.sourceOrange)>30;
            if(menuVisible)globalThis.__riMenuPixels={left,top:menu.top,width:captureWidth,height:captureHeight,canvasWidth:width,canvasHeight:height,data:flipped};
            else if(globalThis.__riMenuRequested===false)globalThis.__riMenuPixels=null;
            if(menuVisible){globalThis.__riMenuCachedPixels=globalThis.__riMenuPixels;globalThis.__riMenuCaptureTime=performance.now();globalThis.__riMenuOpening=false;}
            const toast=rule.suppressBalanceToast;
            if(menuVisible&&toast){
              const scanX=Math.min(width-1,Math.max(0,500)),scan=new Uint8Array(height*4);
              gl.readPixels(scanX,0,1,height,gl.RGBA,gl.UNSIGNED_BYTE,scan);
              let chartBottom=height-66,run=0;
              for(let y=300;y<height-30;y++){
                const at=(height-1-y)*4;
                const match=Math.abs(scan[at]-48)<=2&&Math.abs(scan[at+1]-43)<=2&&Math.abs(scan[at+2]-40)<=2;
                run=match?run+1:0;
                if(run>=18){chartBottom=y-run+1;break;}
              }
              const toastTop=Math.max(0,chartBottom-toast.topFromChartBottom);
              const toastBottom=Math.min(height,chartBottom-toast.bottomFromChartBottom);
              const toastWidth=toast.right-toast.left,toastHeight=toastBottom-toastTop;
              const toastRaw=new Uint8Array(toastWidth*toastHeight*4);
              gl.readPixels(toast.left,height-toastBottom,toastWidth,toastHeight,gl.RGBA,gl.UNSIGNED_BYTE,toastRaw);
              const toastFlipped=new Uint8ClampedArray(toastRaw.length),toastRow=toastWidth*4;
              for(let y=0;y<toastHeight;y++)toastFlipped.set(toastRaw.subarray((toastHeight-1-y)*toastRow,(toastHeight-y)*toastRow),y*toastRow);
              globalThis.__riToastGuardPixels={left:toast.left,top:toastTop,width:toastWidth,height:toastHeight,data:toastFlipped,chartBottom};
            }
            globalThis.dispatchEvent?.(new Event('render-inspector-menu-change'));
          }catch{}
        });
      }
      return result;
    });
    globalThis.__renderInspector?.emit?.('WEBGL_EDITOR_INSTALLED',{ruleId:rule.id,canvasId:globalThis.__renderInspector.id('canvas',canvas)});
  };
})();
