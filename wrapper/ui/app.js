"use strict";
const PERSONA = "customer_support";
const $ = id => document.getElementById(id);
const state = {
  samples: [], context: {}, pending: false, latest: null, history: [], audit: [],
  started: 0, timer: null, toastTimer: null, focusBeforeAudit: null
};
const esc = value => String(value ?? "").replace(/[&<>"']/g, char =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const present = value => {
  if (value === null || value === undefined || value === "") return "Not supplied";
  if (Array.isArray(value)) return value.map(present).join(", ");
  if (typeof value === "object") return Object.entries(value)
    .map(([key,val]) => key.replaceAll("_", " ") + ": " + present(val)).join(" · ");
  return String(value);
};
const styleFor = decision => ({APPROVE:"approve",HOLD_FOR_REVIEW:"hold",BLOCK:"block"}[decision] || "unknown");
const titleFor = decision => ({
  APPROVE:"Ready to send",HOLD_FOR_REVIEW:"A manager should review",BLOCK:"This promise fails the check"
}[decision] || "Decision unavailable");
const labelFor = decision => ({
  APPROVE:"✓ APPROVE",HOLD_FOR_REVIEW:"◷ HOLD FOR REVIEW",BLOCK:"⊘ BLOCK"
}[decision] || "UNKNOWN");
const chip = decision => '<span class="decision-chip ' + styleFor(decision) + '">' + esc(labelFor(decision)) + '</span>';
const time = value => {
  const date = value ? new Date(value) : new Date();
  return Number.isNaN(date.getTime()) ? "Time unavailable" :
    date.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});
};
const actionLabel = result => result.action_executed === true ? "✓ Mock email executed" :
  result.action_executed === false ? "⊘ Email action withheld" : "? Action status unknown";
const contextLabel = context => (context?.plan || "Unknown plan") + " · " +
  (context?.customer_tenure_months ?? "Unknown") + " months";

async function request(path, options) {
  let response;
  try { response = await fetch(path, options); }
  catch { throw new Error("Connection interrupted. The outcome is unknown; inspect the audit trail before sending again."); }
  let body;
  try { body = await response.json(); }
  catch { throw new Error("The server returned an unreadable response. Inspect the audit trail before retrying."); }
  if (!response.ok) throw new Error(body.error || ("Request failed (" + response.status + ")."));
  return body;
}
// The browser presents the backend decision. It never checks policy or executes an action.
async function decide(text, context) {
  return request("/decide", {
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify({text,persona:PERSONA,context})
  });
}
function showError(message) {
  $("request-error").textContent = message;
  $("request-error").hidden = false;
}
function clearError() { $("request-error").hidden = true; $("request-error").textContent = ""; }
function toast(message) {
  clearTimeout(state.toastTimer); $("toast").textContent=message; $("toast").hidden=false;
  state.toastTimer=setTimeout(()=>{$("toast").hidden=true;},5000);
}
function setPending(pending, label="Checking policy and Ezio signals") {
  state.pending = pending;
  document.querySelectorAll(".request-control").forEach(el => el.disabled = pending);
  $("decision-panel").setAttribute("aria-busy", String(pending));
  $("request-status").hidden = !pending;
  clearInterval(state.timer);
  if (pending) {
    state.started=Date.now();
    const update=()=>{
      const elapsed=Math.floor((Date.now()-state.started)/1000);
      $("request-status-text").textContent=label + " · " + elapsed + "s" +
        (elapsed>=12 ? " · still waiting; retries may be in progress" : "");
    };
    update(); state.timer=setInterval(update,1000);
  }
}
function readDraft() {
  const text=$("text").value;
  if(!text.trim()) throw new Error("Enter an email draft before checking it.");
  if(text.length>20000) throw new Error("Keep the draft within 20,000 characters.");
  const context={...state.context};
  if($("plan").value) context.plan=$("plan").value; else delete context.plan;
  if($("tenure").value.trim()) {
    const tenure=Number($("tenure").value);
    if(!Number.isInteger(tenure)||tenure<0||tenure>1200)
      throw new Error("Customer tenure must be a whole number from 0 to 1,200 months, or left blank.");
    context.customer_tenure_months=tenure;
  } else delete context.customer_tenure_months;
  return {text,context};
}
function loadDraft(text,context={}) {
  state.context={...context}; $("text").value=text;
  $("plan").value=context.plan || "";
  $("tenure").value=context.customer_tenure_months ?? "";
  draftChanged();
}
function draftChanged() {
  $("character-count").textContent=$("text").value.length.toLocaleString() + " / 20,000";
  const stale=$("stale-result");
  if(stale&&state.latest) {
    let same=false;
    try {
      const draft=readDraft();
      same=draft.text===state.latest.text&&JSON.stringify(draft.context)===JSON.stringify(state.latest.context);
    } catch {}
    stale.hidden=same;
  }
}
function addHistory(result,text,context,label="Current customer") {
  const entry={result,text,context:{...context},label,at:new Date().toISOString()};
  state.history.unshift(entry); state.history=state.history.slice(0,12);
  renderHistory(); return entry;
}
function witnessMarkup(witness) {
  const found=witness.outcome==="counterexample_found";
  const insufficient=witness.outcome==="insufficient_information";
  const title=found ? "A customer this promise fails" : insufficient ? "More context is needed" : "No counterexample found";
  const symbol=found?"⊘":insufficient?"?":"✓";
  const customer=witness.customer && Object.keys(witness.customer).length ? witness.customer :
    (witness.scope ? witness.scope[0].toUpperCase()+witness.scope.slice(1)+" claim" : "Modeled discount scope");
  return '<article class="witness ' + (!found&&!insufficient?"pass":"") + '">' +
    '<div class="witness-top"><p class="eyebrow">' + esc(title) + '</p><span aria-hidden="true">' + symbol + '</span></div>' +
    '<h3>' + esc(present(customer)) + '</h3>' +
    (witness.claim?'<p>Claim: “'+esc(witness.claim)+'”</p>':"") +
    '<dl>' +
    (witness.claimed_benefit?'<dt>Promised</dt><dd>'+esc(present(witness.claimed_benefit))+'</dd>':"") +
    (witness.failed_condition?'<dt>Fails because</dt><dd>'+esc(present(witness.failed_condition))+'</dd>':"") +
    (witness.expected!==undefined&&witness.expected!==null?'<dt>Policy requires</dt><dd>'+esc(present(witness.expected))+'</dd>':"") +
    '</dl><p class="source">Source: '+esc(present(witness.source)) +
    (witness.policy_field?' · '+esc(witness.policy_field):"")+'</p></article>';
}
function checksMarkup(checks) {
  if(!Array.isArray(checks)||!checks.length)return "";
  return '<p class="section-label">Source-of-truth checks</p><div class="checks">' +
    checks.map(check=>'<div class="check-row"><div class="check-heading"><strong>'+
      esc(present(check.claim))+'</strong><span class="pill">'+
      esc(present(check.status).replaceAll("_"," "))+'</span></div>'+
      '<div class="check-values"><span>Draft: <b>'+esc(present(check.actual))+
      '</b></span><span>Expected: <b>'+esc(present(check.expected))+
      '</b></span></div><div class="source">'+esc(present(check.source))+'</div></div>').join("")+'</div>';
}
function signalsMarkup(result) {
  const ezio=result.ezio||{},verdict=ezio.verdict||{},dims=ezio.dimensions||{},accuracy=dims.accuracy||{};
  const status=accuracy.status?accuracy.status.replaceAll("_"," "):ezio.error?"service unavailable":"not supplied";
  const metric=key=>{
    const value=dims[key]?.score;
    const number=typeof value==="number"&&Number.isFinite(value)?value:null;
    return '<div class="signal"><small>'+esc(key[0].toUpperCase()+key.slice(1))+
      '</small><strong>'+(number===null?"—":esc(number))+'</strong>'+
      '<div class="bar"><span style="width:'+(number===null?0:Math.max(0,Math.min(100,number)))+
      '%"></span></div><div class="mini">Score / 100</div></div>';
  };
  return '<div class="signals"><div class="signal"><small>Ezio signal</small><strong>'+
    esc(verdict.tier||"Unavailable")+(verdict.score!==undefined?' <span style="font-size:12px">'+esc(verdict.score)+'</span>':"")+
    '</strong><div class="mini">Accuracy: '+esc(status)+'<br>Gate decides independently.</div></div>'+
    metric("tone")+metric("bias")+metric("agreement")+'</div>';
}
function renderResult(entry) {
  state.latest=entry; const result=entry.result;
  const witnesses=Array.isArray(result.counterexamples)?result.counterexamples:[];
  const evidence=Array.isArray(result.evidence)?result.evidence:[];
  const review=result.decision==="HOLD_FOR_REVIEW"&&result.decision_id;
  $("empty-state").hidden=true; $("result-content").hidden=false; $("result-time").textContent=time(entry.at);
  $("result-content").innerHTML='<div class="result-main">'+
    '<div class="notice stale" id="stale-result" hidden>This decision belongs to another draft or customer context. Check the current draft before sending.</div>'+
    '<div class="decision-top"><div><p class="decision-label">'+esc(contextLabel(entry.context))+
    '</p><h2 class="decision-title">'+esc(titleFor(result.decision))+'</h2></div>'+chip(result.decision)+'</div>'+
    '<p class="reason">'+esc(result.reason||"No reason returned.")+'</p>'+
    '<div class="action-banner"><strong>'+esc(actionLabel(result))+'</strong></div>'+signalsMarkup(result)+
    (witnesses.length?'<p class="section-label">Challenge the claim</p>'+witnesses.map(witnessMarkup).join(""):"")+
    checksMarkup(result.checks)+'<details '+(!witnesses.length&&!result.checks?.length?"open":"")+
    '><summary class="section-label">Supporting evidence · '+evidence.length+'</summary><ul class="evidence-list">'+
    (evidence.length?evidence.map(line=>'<li>'+esc(present(line))+'</li>').join(""):"<li>The server supplied no supporting evidence.</li>")+
    '</ul></details>'+
    (review?'<form class="review" id="review-form"><strong style="font-size:13px">Manager review</strong>'+
      '<p>Log a reason to reject or request revision. A revised email must pass the gate again.</p>'+
      '<label for="review-note">Review rationale</label><textarea id="review-note" maxlength="1000" class="request-control" '+
      'placeholder="Explain what needs to change, or why this draft should be rejected." required></textarea>'+
      '<div class="review-controls"><select id="review-disposition" class="request-control" aria-label="Review disposition">'+
      '<option value="request_revision">Request revision</option><option value="reject">Reject draft</option></select>'+
      '<button class="button request-control" type="submit">Log review</button></div></form>':"")+
    (result.decision_id?'<div class="audit-id">Decision '+esc(result.decision_id)+'</div>':"")+'</div>';
  if(review)$("review-form").addEventListener("submit",submitReview);
  draftChanged();
}
function renderHistory() {
  $("session-history").innerHTML=state.history.slice(0,6).map((entry,index)=>
    '<article class="history-card">'+chip(entry.result.decision)+'<p>'+esc(entry.text)+'</p>'+
    '<div class="history-meta">'+esc(entry.label)+' · '+esc(contextLabel(entry.context))+'</div>'+
    '<div class="history-action">'+esc(actionLabel(entry.result))+'</div>'+
    '<button class="button small request-control" type="button" data-history="'+index+'">Inspect evidence</button></article>').join("");
  document.querySelectorAll("[data-history]").forEach(button=>{
    button.disabled=state.pending;
    button.addEventListener("click",()=>renderResult(state.history[Number(button.dataset.history)]));
  });
}
async function submitDraft(event) {
  event.preventDefault(); if(state.pending)return; clearError(); let draft;
  try{draft=readDraft();}catch(error){showError(error.message);return;}
  setPending(true);
  try{const result=await decide(draft.text,draft.context);renderResult(addHistory(result,draft.text,draft.context));}
  catch(error){showError(error.message);}
  finally{setPending(false);}
}
async function compareBoundary() {
  if(state.pending)return; clearError(); let draft;
  try{draft=readDraft();}catch(error){showError(error.message);return;}
  const contexts=[
    {...draft.context,plan:"Pro",customer_tenure_months:11},
    {...draft.context,plan:"Pro",customer_tenure_months:12}
  ];
  const output=$("boundary-output"); output.hidden=false;
  output.innerHTML='<div class="boundary-draft">Same draft: “'+esc(draft.text)+'”</div><div class="boundary-results">'+
    contexts.map((context,index)=>'<article class="boundary-result" id="boundary-'+index+'">'+
    '<span class="small-label">HYPOTHETICAL PRO CUSTOMER</span><h3>'+context.customer_tenure_months+
    ' months</h3><div class="boundary-loading">Waiting for backend decision…</div></article>').join("")+'</div>';
  setPending(true,"Comparing two hypothetical customers");
  try{
    // Two real requests; no expected decisions are supplied or inferred in the browser.
    const results=await Promise.allSettled(contexts.map(context=>decide(draft.text,context)));
    results.forEach((response,index)=>{
      const context=contexts[index],container=$("boundary-"+index);
      const header='<span class="small-label">HYPOTHETICAL PRO CUSTOMER</span><h3>'+context.customer_tenure_months+' months</h3>';
      if(response.status==="rejected"){
        container.innerHTML=header+'<p class="reason">'+esc(response.reason.message)+'</p><div class="action">? Action status unknown</div>';
        return;
      }
      const result=response.value,entry=addHistory(result,draft.text,context,"Boundary test");
      const found=(Array.isArray(result.counterexamples)?result.counterexamples:[]).find(witness=>witness.outcome==="counterexample_found");
      container.innerHTML=header+chip(result.decision)+'<p class="reason">'+
        esc(found?.failed_condition?present(found.failed_condition):result.reason)+
        '</p><div class="action">'+esc(actionLabel(result))+'</div>'+
        '<button class="button small request-control" style="margin-top:12px" type="button">Inspect evidence</button>';
      container.querySelector("button").disabled=true;
      container.querySelector("button").addEventListener("click",()=>{
        renderResult(entry);$("decision-panel").scrollIntoView({behavior:"smooth",block:"start"});
      });
    });
  }catch(error){showError(error.message);}
  finally{setPending(false);}
}
async function submitReview(event) {
  event.preventDefault(); if(state.pending||!state.latest)return;
  const note=$("review-note").value.trim(),disposition=$("review-disposition").value,entry=state.latest;
  if(!note){toast("Add a rationale before recording the review.");$("review-note").focus();return;}
  clearError();setPending(true,"Recording manager review");
  try{
    await request("/api/reviews",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({decision_id:entry.result.decision_id,disposition,note})
    });
    if(disposition==="request_revision"){
      loadDraft(entry.text,entry.context);
      toast("Revision requested and logged. Edit the draft, then run a fresh check.");
    }else toast("Rejection logged. The held email remains unsent.");
    const form=$("review-form");
    if(form)form.innerHTML='<div class="notice">'+(disposition==="reject"?"Draft rejected":"Revision requested")+
      '. Review rationale logged: '+esc(note)+'. No action was executed by this review.</div>';
  }catch(error){showError(error.message);}
  finally{setPending(false);if(disposition==="request_revision")$("text").focus();}
}
function renderAudit() {
  $("audit-body").innerHTML=state.audit.length?state.audit.map((entry,index)=>
    '<article class="audit-item"><div class="audit-top">'+chip(entry.decision)+
    '<span class="audit-time">'+esc(time(entry.timestamp))+'</span></div>'+
    '<h3>'+esc(entry.input||entry.text||"Input unavailable")+'</h3>'+
    '<p>'+esc(contextLabel(entry.context))+'</p><p>'+esc(entry.reason||"No reason supplied")+'</p>'+
    '<details><summary>Supporting evidence</summary><ul class="evidence-list">'+
    (Array.isArray(entry.evidence)?entry.evidence:[]).map(line=>'<li>'+esc(present(line))+'</li>').join("")+'</ul></details>'+
    (Array.isArray(entry.reviews)?entry.reviews:[]).map(review=>
      '<div class="review-entry"><strong>'+esc(review.disposition==="reject"?"Rejected":"Revision requested")+
      '</strong> · '+esc(time(review.timestamp))+'<p>'+esc(review.note)+'</p></div>').join("")+
    (entry.decision==="HOLD_FOR_REVIEW"?'<button class="button small request-control" type="button" data-audit="'+
      index+'" style="margin-top:12px">Open for manager review</button>':"")+
    '<div class="audit-id">'+esc(entry.decision_id||"Decision ID unavailable")+'</div></article>').join(""):
    '<p class="small-label">No decision records yet. Check a draft to create a persistent audit entry.</p>';
  document.querySelectorAll("[data-audit]").forEach(button=>button.addEventListener("click",()=>{
    const entry=state.audit[Number(button.dataset.audit)];
    const result={
      decision:entry.decision,reason:entry.reason,evidence:entry.evidence,ezio:entry.ezio,
      checks:entry.checks,counterexamples:entry.counterexamples,decision_id:entry.decision_id,
      action_executed:entry.action_executed
    };
    loadDraft(entry.input||entry.text||"",entry.context||{});
    renderResult({result,text:entry.input||entry.text||"",context:entry.context||{},at:entry.timestamp,label:"Audit record"});
    closeAudit();$("review-note")?.focus();
  }));
}
async function refreshAudit() {
  if(state.pending)return;setPending(true,"Loading persistent audit trail");
  try{
    const body=await request("/api/audit");state.audit=Array.isArray(body.entries)?body.entries:[];renderAudit();
  }catch(error){$("audit-body").innerHTML='<div class="error" role="alert">'+esc(error.message)+'</div>';}
  finally{setPending(false);}
}
function openAudit() {
  state.focusBeforeAudit=document.activeElement;$("audit-modal").hidden=false;
  document.body.style.overflow="hidden";$("audit-dialog").focus();refreshAudit();
}
function closeAudit() {
  $("audit-modal").hidden=true;document.body.style.overflow="";state.focusBeforeAudit?.focus();
}
$("draft-form").addEventListener("submit",submitDraft);
$("compare").addEventListener("click",compareBoundary);
$("load-sample").addEventListener("click",()=>{
  const sample=state.samples.find(item=>item.id===$("samples").value);
  if(sample){loadDraft(sample.text,sample.context);toast("Practice draft loaded with its customer context. Check it to see the gate's decision.");}
});
["text","plan","tenure"].forEach(id=>$(id).addEventListener("input",draftChanged));
$("open-audit").addEventListener("click",openAudit);
$("close-audit").addEventListener("click",closeAudit);
$("refresh-audit").addEventListener("click",refreshAudit);
$("audit-modal").addEventListener("click",event=>{if(event.target===$("audit-modal"))closeAudit();});
document.addEventListener("keydown",event=>{
  if($("audit-modal").hidden)return;
  if(event.key==="Escape"){closeAudit();return;}
  if(event.key==="Tab"){
    const items=[...$("audit-dialog").querySelectorAll(
      "button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex='0']")];
    const first=items[0],last=items[items.length-1];
    if(!first){event.preventDefault();return;}
    if(event.shiftKey&&(document.activeElement===first||document.activeElement===$("audit-dialog"))){
      event.preventDefault();last.focus();
    }else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}
  }
});
async function init() {
  draftChanged();
  try{
    const body=await request("/api/samples?persona="+PERSONA);
    state.samples=Array.isArray(body.samples)?body.samples:[];
    $("samples").innerHTML=state.samples.length?state.samples.map(item=>
      '<option value="'+esc(item.id)+'">'+esc(item.id)+' · '+esc(item.text.slice(0,57))+
      (item.text.length>57?"…":"")+'</option>').join(""):'<option value="">No practice inputs available</option>';
  }catch(error){
    $("samples").innerHTML='<option value="">Practice inputs unavailable</option>';showError(error.message);
  }
}
init();
