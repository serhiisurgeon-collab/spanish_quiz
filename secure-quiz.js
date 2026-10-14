/* The server owns progress; browser state is only a durable retry request. */
window.startSecureQuiz = async function(tg, params) {
  const lang=['uk','en'].includes(params.get('lang'))?params.get('lang'):'uk';
  const level=['A1','A2','B1'].includes(params.get('level'))?params.get('level'):'A1';
  const d=window.QuizLocales[lang], t=(key,values={})=>d[key].replace(/\{(\w+)\}/g,(_,k)=>values[k]);
  const el=id=>document.getElementById(id),next=el('nextBtn'),finish=el('finishBtn'),error=el('error');
  document.documentElement.lang=lang;document.title=t('title');el('quizTitle').textContent=t('heading');el('questionPrompt').textContent=t('prompt');el('levelBadge').textContent=t('level',{level});
  el('hint').textContent=t('secureHint');next.textContent=t('next');finish.textContent=t('secureFinish');next.disabled=true;finish.disabled=true;
  const retry=document.createElement('button');retry.textContent=t('retry');retry.hidden=true;error.parentNode?.appendChild(retry);
  const base=(window.QuizConfig?.apiBase||'').replace(/\/$/,'');
  if(!base||params.get('api')?.replace(/\/$/,'')!==base||!tg.initData){error.textContent=t('outside');return;}
  let key=null,state=null,sid=null,position=0,current=null,busy=false,answered=false,terminal=false,retryAction=null;
  const save=()=>{if(key&&state)try{sessionStorage.setItem(key,JSON.stringify(state));}catch(_){}};
  const clear=()=>{try{sessionStorage.removeItem(key);}catch(_){}};
  function lock(){next.disabled=true;finish.disabled=true;for(const b of el('optionsContainer').querySelectorAll('button'))b.disabled=true;}
  function failure(e,action){
    terminal=['auth_expired','access_denied'].includes(e.code);error.textContent=t(e.code==='auth_expired'?'authExpired':e.code==='access_denied'?'accessDenied':e.code==='server'?'serverError':e.code==='invalid'?'requestError':e.code==='timeout'?'timeoutError':'networkError');
    retryAction=action;retry.hidden=terminal;lock();
  }
  async function call(path,body){
    const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),15000);
    try{
      const response=await fetch(base+path,{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,initData:tg.initData})});
      const data=await response.json();
      if(!response.ok){const e=new Error('API');e.code=data.error==='auth_expired'?'auth_expired':response.status===401||response.status===403?'access_denied':response.status>=500?'server':'invalid';throw e;}
      return data;
    }catch(e){if(!e.code)e.code=e.name==='AbortError'?'timeout':'network';throw e;}finally{clearTimeout(timer);}
  }
  async function perform(action){
    if(busy||terminal)return;busy=true;retry.hidden=true;error.textContent='';lock();
    try{await action();}catch(e){failure(e,action);}finally{busy=false;}
  }
  retry.onclick=()=>perform(retryAction);
  function feedback(q){
    answered=true;el('result').textContent=q.correct?t('correct',{word:q.es,answer:q.answer}):t('wrong',{answer:q.answer});
    if(q.example)el('exampleText').textContent+='\n'+t('exampleTranslation',{example:q.example});
    for(const b of el('optionsContainer').querySelectorAll('button')){b.disabled=true;if(b.textContent===q.answer)b.classList.add('correct');else if(b.textContent===q.chosen)b.classList.add('wrong');}
  }
  function progress(data){
    if(!Number.isInteger(data.total)||!Number.isInteger(data.accepted_total))return;
    const total=data.total, count=data.accepted_total;
    if(total<=0||count<0||count>total)return;
    el('quizProgress').hidden=false;el('progressAccepted').textContent=String(count);el('progressTotal').textContent=String(total);
    el('progressFill').style.width=(count/total*100)+'%';
    const bar=el('progressBar');bar.setAttribute('aria-valuemax',String(total));bar.setAttribute('aria-valuenow',String(count));
    const label=t('progressDescription',{count,total});bar.setAttribute('aria-valuetext',label);bar.setAttribute('aria-label',label);
  }
  function render(q,status){
    progress(q);
    current=q;position=q.position;state.position=position;answered=false;el('wordText').textContent=q.es;el('exampleText').textContent=q.context?t('context',{example:q.context}):'';el('result').textContent='';el('optionsContainer').innerHTML='';
    if(status==='completed'){
      clear();terminal=true;el('result').textContent=t('secureSummary',q.summary);el('hint').textContent=t('secureFinished');lock();return;
    }
    for(const option of q.options){
      const button=document.createElement('button');button.className='option';button.textContent=option;
      button.onclick=()=>{
        if(busy||answered||state.pending)return;
        state.pending={session_id:sid,position,chosen:option};save();
        return perform(resolvePending);
      };
      el('optionsContainer').appendChild(button);
    }
    if(q.accepted){state.pending=null;feedback(q);}
    next.disabled=!answered||position>=q.total-1;finish.disabled=q.accepted_total===0;
    el('hint').textContent=t('secureCount',{count:q.accepted_total});save();
  }
  async function load(target){
    const result=await call('/quiz/question',{session_id:sid,...(target===undefined?{}:{position:target})});
    render(result.question,result.status);
  }
  async function resolvePending(){
    const pending=state.pending;
    if(!pending)return load();
    const snapshot=await call('/quiz/question',{session_id:sid,position:pending.position});
    if(!snapshot.question.accepted&&snapshot.status!=='completed'){
      const accepted=await call('/quiz/answer',pending);progress(accepted);
    }
    // A lost reply is reconciled from the server; never offer another choice meanwhile.
    await load(pending.position);
  }
  next.onclick=()=>{
    if(busy||!answered||terminal)return;
    const target=position+1;
    return perform(()=>load(target)); // position is committed only by successful render().
  };
  finish.onclick=()=>{
    if(busy||terminal||state.pending||!current||current.accepted_total===0)return;
    return perform(async()=>{
      const result=await call('/quiz/complete',{session_id:sid});progress(result);clear();terminal=true;
      el('result').textContent=t('secureSummary',result);el('optionsContainer').innerHTML='';el('hint').textContent=t('secureFinished');lock();
    });
  };
  async function boot(){
    const identity=await call('/quiz/identity',{});
    key='verifiedQuiz:'+identity.user_id+':'+level+':'+lang;
    if(!state){try{state=JSON.parse(sessionStorage.getItem(key)||'null');}catch(_){state=null;}}
    if(!state){
      // Migrate an old unbound browser record only after server ownership verification.
      const legacyKey='verifiedQuiz:'+level+':'+lang;
      let legacy;try{legacy=JSON.parse(sessionStorage.getItem(legacyKey)||'null');}catch(_){legacy=null;}
      if(legacy?.sid&&typeof legacy.request_id==='string'){
        try{
          const verified=await call('/quiz/question',{session_id:legacy.sid});
          if(verified.question.user_id===identity.user_id&&verified.question.level===level&&verified.question.language===lang){
            state={request_id:legacy.request_id,sid:legacy.sid};try{sessionStorage.removeItem(legacyKey);}catch(_){}
          }
        }catch(e){if(e.code!=='access_denied'&&e.code!=='invalid')throw e;}
      }
    }
    if(!state||typeof state.request_id!=='string')state={request_id:crypto.randomUUID()};
    save();const result=await call('/quiz/session',{level,lang,request_id:state.request_id});sid=result.session_id;state.sid=sid;save();
    if(state.pending&&state.pending.session_id===sid)return resolvePending();
    await load();
  }
  await perform(boot);
};
