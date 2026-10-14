/* Server-authoritative mode. No client Telegram ID, scores or correctness are submitted. */
window.startSecureQuiz = async function(tg, params) {
  const lang = ['uk','en'].includes(params.get('lang')) ? params.get('lang') : 'uk';
  const level = ['A1','A2','B1'].includes(params.get('level')) ? params.get('level') : 'A1';
  const d = window.QuizLocales[lang];
  const t = (key, values={}) => d[key].replace(/\{(\w+)\}/g, (_, k) => values[k]);
  const el = id => document.getElementById(id);
  const next=el('nextBtn'),finish=el('finishBtn'),error=el('error');
  document.documentElement.lang=lang;document.title=t('title');el('quizTitle').textContent=t('heading');
  el('questionPrompt').textContent=t('prompt');el('levelBadge').textContent=t('level',{level});
  next.textContent=t('next');finish.textContent=t('finish');next.disabled=true;finish.disabled=true;
  const base=(window.QuizConfig?.apiBase || '').replace(/\/$/,'');
  if (!base || params.get('api').replace(/\/$/,'')!==base || !tg.initData) {
    error.textContent=t('outside');return;
  }
  let sid=null,position=0,busy=false,answered=false;
  const key='verifiedQuiz:'+level+':'+lang;
  let state;
  try {state=JSON.parse(sessionStorage.getItem(key)||'null');} catch (_) {state=null;}
  if (!state) state={request_id:crypto.randomUUID(),position:0};
  const save=()=>{try {sessionStorage.setItem(key,JSON.stringify(state));}catch (_) {}};
  async function call(path, body) {
    const response=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,initData:tg.initData})});
    if (!response.ok) throw new Error('API unavailable');
    return await response.json();
  }
  async function question() {
    busy=true;next.disabled=true;error.textContent='';
    try {
      const result=await call('/quiz/question',{session_id:sid,position});
      if (result.status==='completed') {sessionStorage.removeItem(key);error.textContent=t('secureFinished');return;}
      const q=result.question;el('wordText').textContent=q.es;el('exampleText').textContent=q.context?t('context',{example:q.context}):'';
      el('result').textContent='';el('optionsContainer').innerHTML='';answered=false;
      for (const option of q.options) {
        const button=document.createElement('button');button.className='option';button.textContent=option;
        button.onclick=async()=>{
          if (busy || answered) return;
          busy=true;error.textContent='';
          try {
            const result=await call('/quiz/answer',{session_id:sid,position,chosen:option});
            answered=true;state.position=position;state.answered=true;save();finish.disabled=false;next.disabled=position>=19;
            el('hint').textContent=t('secureCount',{count:position+1});
            el('result').textContent=result.correct?t('correct',{word:q.es,answer:result.answer}):t('wrong',{answer:result.answer});
            if (result.example) el('exampleText').textContent+='\n'+t('exampleTranslation',{example:result.example});
            for (const b of el('optionsContainer').querySelectorAll('button')) {b.disabled=true;if (b.textContent===result.answer)b.classList.add('correct');else if(b===button)b.classList.add('wrong');}
          } catch (_) {error.textContent=t('sendError');} finally {busy=false;}
        };
        el('optionsContainer').appendChild(button);
      }
      if (state.answered) {finish.disabled=false;el('hint').textContent=t('secureResume');}
    } catch (_) {error.textContent=t('sendError');} finally {busy=false;}
  }
  next.onclick=async()=>{if(busy||!answered)return;position++;state.position=position;state.answered=false;save();await question();};
  finish.onclick=async()=>{
    if (busy)return;busy=true;finish.disabled=true;next.disabled=true;
    try {
      const result=await call('/quiz/complete',{session_id:sid});
      sessionStorage.removeItem(key);el('result').textContent=t('secureSummary',{correct:result.correct,incorrect:result.incorrect});
      el('optionsContainer').innerHTML='';el('hint').textContent=t('secureFinished');
    } catch (_) {error.textContent=t('sendError');finish.disabled=false;} finally {busy=false;}
  };
  try {
    save();const result=await call('/quiz/session',{level,lang,request_id:state.request_id});sid=result.session_id;state.sid=sid;position=state.position||0;save();await question();
  } catch (_) {error.textContent=t('sendError');}
};
