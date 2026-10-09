(() => {
  const rules = __VISUAL_EDITS__;
  const installed = new WeakSet();
  globalThis.__riInstallWebGL = (gl, canvas, contextType) => {
    const R = globalThis.__renderInspector;
    if (!R || installed.has(gl)) return;
    installed.add(gl);
    globalThis.__riInstallWebGLEditor?.(gl, canvas);
    globalThis.__riInstallFrameCapture?.(gl, canvas);
    const canvasId = R.id("canvas", canvas);
    const contextMeta=R.contexts?.get(R.id("context",gl));if(contextMeta)contextMeta.webglHook=true;
    const rule = Array.isArray(rules) ? rules.find(item => item?.enabled && item.webglUniformRemaps && (!item.canvasId || item.canvasId === canvas.id)) : null;
    const uniformNames = new WeakMap();
    const trace = globalThis.__riFlickerTrace;
    R.webglDraws = R.webglDraws || [];
    const state = {program:null, activeUnit:0, textures:{}, buffers:{}, uniforms:{}, viewport:[], scissor:[],lastDrawEmit:0,uniformRemapExpected:false,uniformRemapApplied:false};
    const emit = (type, payload={}) => R.emit(type, {canvasId, ...payload});
    const wrap = (api, before, after) => {
      const original = gl[api]; if (typeof original !== "function") return;
      gl[api] = function(...args) {
        R.safe(`webgl.${api}.before`, () => before?.(args));
        const result = original.apply(this, args);
        R.safe(`webgl.${api}.after`, () => after?.(args, result));
        return result;
      };
    };
    wrap("createShader", null, (a,o) => emit("WEBGL_SHADER_CREATED", {shaderId:R.id("shader",o), shaderType:a[0]}));
    wrap("shaderSource", a => emit("WEBGL_SHADER_SOURCE", {shaderId:R.id("shader",a[0]), source:String(a[1])}));
    wrap("compileShader", null, a => emit("WEBGL_SHADER_COMPILED", {shaderId:R.id("shader",a[0]), compiled:gl.getShaderParameter(a[0],gl.COMPILE_STATUS), log:gl.getShaderInfoLog(a[0])||""}));
    wrap("createProgram", null, (_a,o) => emit("WEBGL_PROGRAM_CREATED", {programId:R.id("program",o)}));
    wrap("attachShader", a => emit("WEBGL_SHADER_ATTACHED", {programId:R.id("program",a[0]), shaderId:R.id("shader",a[1])}));
    wrap("linkProgram", null, a => emit("WEBGL_PROGRAM_LINKED", {programId:R.id("program",a[0]), linked:gl.getProgramParameter(a[0],gl.LINK_STATUS), log:gl.getProgramInfoLog(a[0])||""}));
    wrap("useProgram", a => { state.program = R.id("program",a[0]); });
    wrap("createTexture", null, (_a,o) => emit("WEBGL_TEXTURE_CREATED", {textureId:R.id("texture",o)}));
    wrap("activeTexture", a => { state.activeUnit = Number(a[0])-Number(gl.TEXTURE0); });
    wrap("bindTexture", a => { state.textures[state.activeUnit] = R.id("texture",a[1]); });
    for (const api of ["texImage2D","texSubImage2D"]) wrap(api, a => emit("WEBGL_TEXTURE_UPLOAD", {
      api, textureId:state.textures[state.activeUnit]||null, activeUnit:state.activeUnit,
      width:typeof a[3]==="number"?a[3]:(a[5]?.width??null), height:typeof a[4]==="number"?a[4]:(a[5]?.height??null),
      sourceKind:a.at(-1)?.constructor?.name || typeof a.at(-1)
    }));
    wrap("createBuffer", null, (_a,o) => emit("WEBGL_BUFFER_CREATED", {bufferId:R.id("buffer",o)}));
    wrap("bindBuffer", a => { state.buffers[a[0]] = R.id("buffer",a[1]); });
    for (const api of ["bufferData","bufferSubData"]) wrap(api, a => emit("WEBGL_BUFFER_DATA", {api,target:a[0],bufferId:state.buffers[a[0]]||null,byteLength:a[1]?.byteLength??(typeof a[1]==="number"?a[1]:null)}));
    wrap("getUniformLocation", null, (a,o) => { const id=R.id("uniform",o); if(o)uniformNames.set(o,String(a[1]));if(id) emit("WEBGL_UNIFORM_LOCATION", {uniformId:id,programId:R.id("program",a[0]),name:String(a[1])}); });
    const uniformApis = ["uniform1f","uniform2f","uniform3f","uniform4f","uniform1i","uniform2i","uniform3i","uniform4i","uniform1fv","uniform2fv","uniform3fv","uniform4fv","uniformMatrix2fv","uniformMatrix3fv","uniformMatrix4fv"];
    for (const api of uniformApis) wrap(api, a => {
      const name=uniformNames.get(a[0]);
      const candidate=rule?.webglUniformRemaps?.find(item=>item.name===name&&(!item.api||item.api===api));
      const raw=a.slice(1).flatMap(v=>ArrayBuffer.isView(v)?Array.from(v):[v]);
      let changed=false;
      if(candidate&&Array.isArray(candidate.from)&&Array.isArray(candidate.to)&&candidate.from.length===raw.length){
        const tolerance=Number(candidate.tolerance??0.002);
        if(raw.every((value,index)=>Math.abs(Number(value)-Number(candidate.from[index]))<=tolerance)){
          state.uniformRemapExpected=true;
          const operation=trace?.begin('OUR_OVERRIDE',{renderer:'WebGL',phase:'uniform',api,name,canvasId});
          if(ArrayBuffer.isView(a[1]))a[1]=new a[1].constructor(candidate.to);else for(let index=0;index<candidate.to.length;index++)a[index+1]=candidate.to[index];
          changed=true;
          state.uniformRemapApplied=true;
          trace?.end('OUR_OVERRIDE',operation,{renderer:'WebGL',phase:'uniform',api,name,canvasId,changed:true});
        }
      }
      const id=R.id("uniform",a[0]); const values=a.slice(1).flatMap(v=>ArrayBuffer.isView(v)?Array.from(v).slice(0,64):[v]); state.uniforms[id]=values; emit("WEBGL_UNIFORM_UPDATED", {uniformId:id,api,values,remapped:changed});
    });
    wrap("viewport", a => { state.viewport=a.slice(0,4).map(Number); });
    wrap("scissor", a => { state.scissor=a.slice(0,4).map(Number); });
    const draws = ["drawArrays","drawElements","drawArraysInstanced","drawElementsInstanced"];
    for (const api of draws) {let traceOperation=null,tracePayload=null;wrap(api, a => {
      const now=performance.now(); const payload={canvasId,drawId:R.id("draw",{}),api,args:a.map(Number),programId:state.program,textures:Object.values(state.textures).filter(Boolean),buffers:Object.values(state.buffers).filter(Boolean),uniforms:{...state.uniforms},viewport:[...state.viewport],scissor:[...state.scissor],timestamp:now};
      R.webglDraws.push(payload); while(R.webglDraws.length>1200||R.webglDraws[0]?.timestamp<now-2000)R.webglDraws.shift();
      if(R.level==="target"||R.level==="deep"||!state.lastDrawEmit||now-state.lastDrawEmit>250){state.lastDrawEmit=now;R.emit("WEBGL_DRAW",payload);}
      tracePayload={api,canvasId,layer:'api-wrapper',incorrectStateVertices:state.uniformRemapExpected&&!state.uniformRemapApplied?1:0};
      traceOperation=trace?.begin('WEBGL_DRAW',tracePayload);
    },()=>{
      if(traceOperation!=null)trace?.end('WEBGL_DRAW',traceOperation,tracePayload||{api,canvasId,layer:'api-wrapper'});
      traceOperation=null;tracePayload=null;state.uniformRemapExpected=false;state.uniformRemapApplied=false;
    });}
    emit("WEBGL_HOOK_INSTALLED", {contextType});
  };
})();
