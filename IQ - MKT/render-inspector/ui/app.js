const token=document.body.dataset.token, $=s=>document.querySelector(s), counts={};
function render(snapshot){
  $("#state").textContent=snapshot.state;
  $("#targets").innerHTML=(snapshot.targets||[]).filter(t=>["page","iframe","worker","shared_worker","service_worker"].includes(t.type)).map(t=>`<div class="node"><b>${t.type}</b> <code>${escapeHtml(t.url||"about:blank")}</code><br><small>${t.target_id}</small></div>`).join("")||"Nenhum target";
  if(snapshot.lastAnalysis) renderAnalysis(snapshot.lastAnalysis);
}
function renderAnalysis(a){
  const c=a.candidates?.[0], d=c?.data||{}, esc=value=>escapeHtml(String(value??""));
  $("#analysis").classList.remove("muted");
  const spatial=c?.kind==="WebGL frame / spatial evidence";
  const spatialRows=spatial?`<dt>Comandos capturados</dt><dd>${esc(d.drawCount)}</dd>
    <dt>Desenhos na posição</dt><dd>${esc(d.spatialMatches?.length||0)}</dd>
    <dt>Desenhos que mudaram o pixel</dt><dd>${esc((d.pixelChanges||[]).filter(x=>x.api!=="clear").length)}</dd>
    <dt>Desenhos sem geometria resolvida</dt><dd>${esc(d.unsupportedDraws?.length||0)}</dd>
    <dt>Componente da interface</dt><dd>Ainda não identificado; contribuição de pixels não confirma o componente.</dd>`:"";
  const details=spatial?`<details><summary>Detalhes da geometria e limitações</summary><pre>${esc(JSON.stringify(d,null,2))}</pre></details>`:"";
  $("#analysis").innerHTML=`<dl><dt>Status</dt><dd><b>${esc(a.status)}</b></dd><dt>Renderer</dt><dd>${esc(a.renderer)}</dd>
    <dt>Frame</dt><dd>${esc(a.selection.frame_id||"sem frame")}</dd><dt>Posição</dt><dd>${esc(a.selection.client_x)}, ${esc(a.selection.client_y)}</dd>
    <dt>Candidato</dt><dd>${esc(c?`${c.kind} — ${c.status}`:"nenhum confirmado")}</dd>${spatialRows}
    <dt>Evidência</dt><dd>${esc(c?.evidence?.join("; ")||a.limitations.join("; "))}</dd>
    <dt>Limitações</dt><dd>${esc(a.limitations.join("; "))}</dd>
    <dt>Artefatos</dt><dd>${a.artifacts.map(x=>`${esc(x.path)} (${esc(x.sha256.slice(0,12))}…)`).join("<br>")}</dd></dl>${details}`;
}
function metrics(){$("#instrumentation").innerHTML=["HOOK_INSTALLED","CANVAS_CONTEXT_CREATED","CANVAS2D_TEXT","WEBGL_DRAW","TARGET_SELECTED","HOOK_FAILED"].map(k=>`<div class="metric">${k}<br><b>${counts[k]||0}</b></div>`).join("")}
function event(e){counts[e.type]=(counts[e.type]||0)+1;metrics();const li=document.createElement("li");li.textContent=`${e.type} ${e.payload?.frameId||""}`;$("#events").prepend(li);while($("#events").children.length>60)$("#events").lastChild.remove();if(e.type==="ANALYSIS_COMPLETED")renderAnalysis(e.payload);if(e.type==="STATE_CHANGED")$("#state").textContent=e.payload.state}
function escapeHtml(s){const el=document.createElement("span");el.textContent=s;return el.innerHTML}
const ws=new WebSocket(`ws://${location.host}/ws?token=${encodeURIComponent(token)}`);ws.onopen=()=>{$("#connection").textContent="CONECTADO";$("#connection").className="pill ok"};ws.onmessage=m=>{const e=JSON.parse(m.data);e.type==="SNAPSHOT"?render(e.payload):event(e)};ws.onclose=()=>{$("#connection").textContent="DESCONECTADO";$("#connection").className="pill warn"};
$("#inspect").onclick=async()=>{const b=$("#inspect");b.disabled=true;try{const r=await fetch(`/api/inspect?token=${encodeURIComponent(token)}`,{method:"POST"});const d=await r.json();b.textContent=`ARMADO EM ${d.armed} CONTEXTOS`;setTimeout(()=>{b.textContent="INSPECIONAR ALVO";b.disabled=false},1600)}catch(e){b.disabled=false;b.textContent="ERRO — TENTAR DE NOVO"}};metrics();
