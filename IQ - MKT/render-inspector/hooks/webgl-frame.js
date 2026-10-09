(() => {
  const installed = new WeakSet();
  globalThis.__riInstallFrameCapture = (gl, canvas) => {
    const R = globalThis.__renderInspector;
    if (!R || installed.has(gl)) return;
    installed.add(gl);
    const shadows = new WeakMap(), versions = new WeakMap(), textures = new Map();
    const MAX_BYTES = 16 * 1024 * 1024;
    let retained = 0, active = null;
    const wrap = (name, action) => {
      const original = gl[name];
      if (typeof original !== 'function') return;
      gl[name] = function(...args) { return action(original, this, args); };
    };
    const bound = target => {
      const enums = new Map([[gl.ARRAY_BUFFER, gl.ARRAY_BUFFER_BINDING], [gl.ELEMENT_ARRAY_BUFFER, gl.ELEMENT_ARRAY_BUFFER_BINDING]]);
      return enums.has(target) ? gl.getParameter(enums.get(target)) : null;
    };
    const bytes = (source, offset = 0, length) => {
      if (source instanceof ArrayBuffer) return new Uint8Array(source);
      if (!ArrayBuffer.isView(source)) return null;
      const unit = source.BYTES_PER_ELEMENT || 1;
      const size = length === undefined || length === 0 ? source.byteLength-offset*unit : length*unit;
      return new Uint8Array(source.buffer, source.byteOffset+offset*unit, size);
    };
    wrap('bufferData', (fn, self, args) => {
      const result = fn.apply(self, args);
      R.safe('frame.bufferData', () => {
        const buffer = bound(args[0]); if (!buffer) return;
        retained -= shadows.get(buffer)?.byteLength || 0;
        shadows.delete(buffer);
        const data = typeof args[1] === 'number' ? null : bytes(args[1], args[3], args[4]);
        const size = typeof args[1] === 'number' ? args[1] : data?.byteLength;
        if (size >= 0 && retained+size <= MAX_BYTES) {
          shadows.set(buffer, data ? data.slice() : new Uint8Array(size)); retained += size;
          versions.set(buffer,(versions.get(buffer)||0)+1);
        }
      });
      return result;
    });
    wrap('bufferSubData', (fn, self, args) => {
      const result = fn.apply(self, args);
      R.safe('frame.bufferSubData', () => {
        const dest = shadows.get(bound(args[0]));
        const source = bytes(args[2], args[3], args[4]);
        if (dest && source) { dest.set(source, args[1]); const b=bound(args[0]);versions.set(b,(versions.get(b)||0)+1); }
      }); return result;
    });
    wrap('deleteBuffer', (fn, self, args) => {
      retained -= shadows.get(args[0])?.byteLength || 0;
      shadows.delete(args[0]); return fn.apply(self,args);
    });
    let activeUnit = gl.getParameter(gl.ACTIVE_TEXTURE)-gl.TEXTURE0;
    wrap('activeTexture',(fn,self,args)=>{const result=fn.apply(self,args);activeUnit=args[0]-gl.TEXTURE0;return result;});
    wrap('bindTexture',(fn,self,args)=>{const result=fn.apply(self,args);textures.set(`${activeUnit}:${args[0]}`,{unit:activeUnit,target:args[0],id:R.id('texture',args[1])});return result;});
    const encode = data => {
      let string = '';
      for (let i=0;i<data.length;i+=8192) string += String.fromCharCode(...data.subarray(i,i+8192));
      return btoa(string);
    };
    const snapshotBuffer = buffer => {
      if (!buffer) return null;
      const id = R.id('buffer', buffer), data = shadows.get(buffer);
      const key = `${id}@${versions.get(buffer)||0}`;
      if(active.buffers[key]) return {id,version:key};
      if (!data || active.byteCount+data.byteLength > MAX_BYTES) {
        active.limitations.add('Buffer unavailable or capture byte budget exceeded'); return {id, unavailable:true};
      }
      // Immutable versions: streamed buffers may change between draws.
      active.buffers[key] = {id, byteLength:data.byteLength, base64:encode(data)};
      active.byteCount += data.byteLength;
      return {id,version:key};
    };
    const pixel = () => {
      if (gl.getParameter(gl.FRAMEBUFFER_BINDING)) return null;
      if (gl.READ_FRAMEBUFFER_BINDING && gl.getParameter(gl.READ_FRAMEBUFFER_BINDING)) return null;
      if (gl.PIXEL_PACK_BUFFER_BINDING && gl.getParameter(gl.PIXEL_PACK_BUFFER_BINDING)) return null;
      const value = new Uint8Array(4);
      gl.readPixels(active.point.x,active.point.y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,value);
      return Array.from(value);
    };
    const snapshot = (api, args) => {
      const program = gl.getParameter(gl.CURRENT_PROGRAM), programId=R.id('program',program);
      const uniforms = [], attributes = [];
      if (program) {
        if(!active.programs[programId]) active.programs[programId]={shaders:(gl.getAttachedShaders(program)||[]).map(s=>({type:gl.getShaderParameter(s,gl.SHADER_TYPE),source:gl.getShaderSource(s)}))};
        for(let i=0;i<gl.getProgramParameter(program,gl.ACTIVE_UNIFORMS);i++) {
          const info = gl.getActiveUniform(program,i);
          const value = gl.getUniform(program,gl.getUniformLocation(program,info.name));
          const values=ArrayBuffer.isView(value)?Array.from(value):value;
          uniforms.push({name:info.name,type:info.type,size:info.size,value:Array.isArray(values)&&values.length>64?{unavailable:true,length:values.length}:values});
        }
        for(let i=0;i<gl.getProgramParameter(program,gl.ACTIVE_ATTRIBUTES);i++) {
          const info = gl.getActiveAttrib(program,i), location = gl.getAttribLocation(program,info.name);
          attributes.push({name:info.name,shaderType:info.type,shaderSize:info.size,location,enabled:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_ENABLED),
            size:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_SIZE),type:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_TYPE),
            normalized:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_NORMALIZED),stride:gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_STRIDE),
            offset:gl.getVertexAttribOffset(location,gl.VERTEX_ATTRIB_ARRAY_POINTER),
            divisor:gl.VERTEX_ATTRIB_ARRAY_DIVISOR?gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_DIVISOR):0,
            buffer:snapshotBuffer(gl.getVertexAttrib(location,gl.VERTEX_ATTRIB_ARRAY_BUFFER_BINDING))});
        }
      }
      const stack=new Error().stack||'';let stackId=active.stackIds[stack];if(stackId===undefined){stackId=Object.keys(active.stacks).length;active.stackIds[stack]=stackId;active.stacks[stackId]=stack;}
      return {order:active.draws.length,api,args:Array.from(args),programId,
        uniforms,attributes,textures:[...textures.values()],indexBuffer:api.includes('Elements')?snapshotBuffer(gl.getParameter(gl.ELEMENT_ARRAY_BUFFER_BINDING)):null,
        viewport:Array.from(gl.getParameter(gl.VIEWPORT)),scissor:Array.from(gl.getParameter(gl.SCISSOR_BOX)),scissorEnabled:gl.isEnabled(gl.SCISSOR_TEST),
        blendEnabled:gl.isEnabled(gl.BLEND),depthEnabled:gl.isEnabled(gl.DEPTH_TEST),stencilEnabled:gl.isEnabled(gl.STENCIL_TEST),cullEnabled:gl.isEnabled(gl.CULL_FACE),
        colorMask:Array.from(gl.getParameter(gl.COLOR_WRITEMASK)),
        stackId,
        framebufferId:R.id('framebuffer',gl.getParameter(gl.FRAMEBUFFER_BINDING)),before:pixel()};
    };
    for (const api of ['drawArrays','drawElements','drawArraysInstanced','drawElementsInstanced']) wrap(api, (fn,self,args) => {
      if (!active) return fn.apply(self,args);
      if(active.draws.length>=1000||performance.now()-active.startedAt>1200) {active.limitations.add('Draw or capture-time budget exceeded; capture is incomplete');return fn.apply(self,args);}
      let draw;
      try { draw=snapshot(api,args); } catch(error) {active.limitations.add(String(error));}
      const result=fn.apply(self,args);
      if(draw) {try {draw.after=pixel();} catch(error) {active.limitations.add(String(error));} active.draws.push(draw);}
      return result;
    });
    wrap('clear', (fn,self,args) => {
      if(!active)return fn.apply(self,args);
      if(active.draws.length>=1000||performance.now()-active.startedAt>1200) {active.limitations.add('Draw or capture-time budget exceeded; capture is incomplete');return fn.apply(self,args);}
      let entry;
      try {entry={order:active.draws.length,api:'clear',args:Array.from(args),framebufferId:R.id('framebuffer',gl.getParameter(gl.FRAMEBUFFER_BINDING)),before:pixel()};} catch(error) {active.limitations.add(String(error));}
      const result=fn.apply(self,args);
      if(entry) {try {entry.after=pixel();} catch(error) {active.limitations.add(String(error));} active.draws.push(entry);}
      return result;
    });
    // Extensions that bypass the wrapped core draw methods are explicitly unsupported.
    if(!gl.drawArraysInstanced) R.frameCaptureExtensionWarning='ANGLE instancing draws are not intercepted';
    R.frameCaptures = R.frameCaptures || new Map();
    R.frameCaptures.set(R.id('canvas',canvas), (clientX,clientY) => new Promise(resolve => {
      if(active) {resolve({error:'Capture already active'});return;}
      if(typeof canvas.getBoundingClientRect!=='function' || typeof requestAnimationFrame!=='function') {
        resolve({error:'Worker/offscreen coordinate mapping unsupported'});return;
      }
      const rect=canvas.getBoundingClientRect();
      const point={x:Math.floor((clientX-rect.left)*gl.drawingBufferWidth/rect.width),y:gl.drawingBufferHeight-1-Math.floor((clientY-rect.top)*gl.drawingBufferHeight/rect.height)};
      if(point.x<0||point.y<0||point.x>=gl.drawingBufferWidth||point.y>=gl.drawingBufferHeight) {resolve({error:'Point outside drawing buffer'});return;}
      let finished=false, timer, fallback;
      const finish = () => {
        if(finished)return; finished=true;clearTimeout(timer);clearTimeout(fallback);
        const result=active;active=null;if(result)delete result.stackIds;
        resolve(result?{...result,limitations:[...result.limitations],endedAt:performance.now()}:{error:'No animation frame received'});
      };
      timer=setTimeout(finish,2500);
      const begin = boundaryMode => {
        if(finished||active)return;
        active={canvasId:R.id('canvas',canvas),point,rect:rect.toJSON(),width:gl.drawingBufferWidth,height:gl.drawingBufferHeight,
          startedAt:performance.now(),boundaryMode,draws:[],buffers:{},programs:{},stacks:{},stackIds:{},byteCount:0,limitations:new Set(['Texture contents and independent replay are not captured; pixel deltas establish contributions, not exclusive ownership.'])};
        if(boundaryMode==='timer-fallback')active.limitations.add('Animation frames were suspended; captured a timed draw batch instead of one complete frame.');
        else active.limitations.add('Capture spans two animation-frame boundaries; multiple render passes may occur.');
        if(R.frameCaptureExtensionWarning)active.limitations.add(R.frameCaptureExtensionWarning);
      };
      fallback=setTimeout(()=>{begin('timer-fallback');setTimeout(finish,250);},100);
      requestAnimationFrame(() => {
        if(finished)return;
        clearTimeout(fallback);begin('animation-frame');
        requestAnimationFrame(finish);
      });
    }));
  };
})();
