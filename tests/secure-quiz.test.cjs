const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
async function setup(lang='uk',config={}){
 const elements={},calls=[],storage=config.storage||new Map(),accepted=config.accepted||new Map();let completed=false;
 function element(){return {textContent:'',children:[],disabled:false,hidden:false,style:{},attributes:{},setAttribute(k,v){this.attributes[k]=v},parentNode:{appendChild(x){elements.retry=x}},classList:{values:[],add(v){this.values.push(v)}},appendChild(x){this.children.push(x)},querySelectorAll(){return this.children},set innerHTML(x){this.children=[]}};}
 const context={URLSearchParams,AbortController,setTimeout:config.setTimeout||setTimeout,clearTimeout,crypto:{randomUUID:()=> 'request1234567890'},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},window:{QuizConfig:{apiBase:'https://api.example'},...(config.tg?{Telegram:{WebApp:config.tg}}:{})},document:{documentElement:{},getElementById:id=>elements[id]??=element(),createElement:element}};
 let hook=config.hook;
 const normal=async(url,options)=>{
  const body=JSON.parse(options.body);calls.push({url,body});
  if(hook){const result=await hook(url,body,options);if(result)return result;}
  let result;
  if(url.endsWith('/identity'))result={user_id:config.uid||'42'};
  else if(url.endsWith('/session'))result={session_id:'server-session'};
  else if(url.endsWith('/question')){
   const position=body.position??Math.max(0,...accepted.keys());const chosen=accepted.get(position);
   const question={position,id:'stable-'+position,es:'el agua',context:'Bebo agua.',options:['correct','wrong','other','fourth'],total:20,accepted:chosen!==undefined,accepted_total:accepted.size,summary:{correct:1,incorrect:0}};
   if(chosen!==undefined)Object.assign(question,{chosen,correct:chosen==='correct',answer:'correct',example:'Translated example'});
   result={status:completed?'completed':'active',question};
  }else if(url.endsWith('/answer')){
   if(accepted.has(body.position)&&accepted.get(body.position)!==body.chosen)return {ok:false,status:400,json:async()=>({error:'invalid_request'})};
   accepted.set(body.position,body.chosen);result={correct:body.chosen==='correct',answer:'correct',example:'Translated example'};
  }else {completed=true;result={correct:1,incorrect:0};}
  return {ok:true,status:200,json:async()=>result};
 };
 context.fetch=normal;vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'locales.js'),'utf8'),context);vm.runInContext(fs.readFileSync(path.join(root,'secure-quiz.js'),'utf8'),context);
 const open=()=>context.window.startSecureQuiz(config.tg||{initData:'signed-telegram-data'},new URLSearchParams({api:config.bad?'https://evil.example':'https://api.example',lang,learning_language:'es',translation_language:config.translation||lang,level:'A1'}));
 await open();return {elements,calls,storage,accepted,context,open,setHook:h=>hook=h};
}
for(const lang of ['uk','en'])test(lang+' server grading, double-click prevention and completion',async()=>{
 const q=await setup(lang),e=q.elements;
 assert.equal(e.exampleText.textContent.includes('Translated example'),false);
 await e.optionsContainer.children[0].onclick();await e.optionsContainer.children[0].onclick();
 const answers=q.calls.filter(c=>c.url.endsWith('/answer'));assert.equal(answers.length,1);assert.equal('correct' in answers[0].body,false);assert.equal('telegram_id' in answers[0].body,false);
 assert.ok(e.exampleText.textContent.includes('Translated example'));await e.finishBtn.onclick();await e.finishBtn.onclick();assert.equal(q.calls.filter(c=>c.url.endsWith('/complete')).length,1);assert.equal(JSON.parse([...q.storage.values()][0]).completed,true);
});
test('untrusted API receives no initData',async()=>{const q=await setup('en',{bad:true});assert.equal(q.calls.length,0)});
test('next-question failure keeps position and retry advances only after success',async()=>{
 const q=await setup('en'),e=q.elements;await e.optionsContainer.children[0].onclick();
 q.setHook(url=>{if(url.endsWith('/question'))throw Error('offline')});await e.nextBtn.onclick();
 assert.equal(JSON.parse([...q.storage.values()][0]).position,0);assert.equal(e.retry.hidden,false);assert.equal(e.nextBtn.disabled,true);
 q.setHook(null);await e.retry.onclick();assert.equal(JSON.parse([...q.storage.values()][0]).position,1);assert.equal(e.optionsContainer.children[0].disabled,false);
});
test('lost answer acknowledgement locks choices and reconciles without a second answer write',async()=>{
 const q=await setup('en'),e=q.elements;
 q.setHook((url,b)=>{if(url.endsWith('/answer')){q.accepted.set(b.position,b.chosen);throw Error('reply lost')}});
 await e.optionsContainer.children[1].onclick();assert.ok(e.optionsContainer.children.every(b=>b.disabled));
 const before=q.calls.length;await e.optionsContainer.children[0].onclick();assert.equal(q.calls.length,before);
 q.setHook(null);await e.retry.onclick();assert.equal(q.calls.filter(c=>c.url.endsWith('/answer')).length,1);assert.equal(e.nextBtn.disabled,false);assert.ok(e.optionsContainer.children[1].classList.values.includes('wrong'));
});
test('reload restores server answer and next; stale browser position is ignored',async()=>{
 const q=await setup('en');await q.elements.optionsContainer.children[0].onclick();
 const key=[...q.storage.keys()][0];const state=JSON.parse(q.storage.get(key));state.position=19;q.storage.set(key,JSON.stringify(state));
 await q.open();assert.equal(q.elements.nextBtn.disabled,false);assert.equal(JSON.parse(q.storage.get(key)).position,0);assert.ok(q.elements.optionsContainer.children[0].classList.values.includes('correct'));
});
test('AbortController timeout offers a retry, not a different answer',async()=>{
 const q=await setup('en');q.context.setTimeout=callback=>{queueMicrotask(callback);return 0};
 q.setHook((url,b,options)=>{if(url.endsWith('/question'))return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>{const e=Error();e.name='AbortError';reject(e)}))});
 await q.elements.optionsContainer.children[0].onclick();assert.ok(q.elements.error.textContent.includes('timed out'));assert.equal(q.elements.retry.hidden,false);
});
test('expired auth and denied access differ and do not offer unsafe retries',async()=>{
 for(const [status,code,text] of [[401,'auth_expired','expired'],[403,'access_denied','access']]){
  const q=await setup('en',{hook:()=>({ok:false,status,json:async()=>({error:code})})});assert.ok(q.elements.error.textContent.includes(text));assert.equal(q.elements.retry.hidden,true);
 }
});
test('local progress is keyed by server identity',async()=>{
 const storage=new Map();await setup('en',{storage,uid:'42'});await setup('en',{storage,uid:'99'});
 assert.ok(storage.has('verifiedQuiz:42:A1:en'));assert.ok(storage.has('verifiedQuiz:99:A1:en'));
});
test('lost completion reply can be retried without changing session results',async()=>{
 const q=await setup('en');await q.elements.optionsContainer.children[0].onclick();let completedCalls=0;
 q.setHook(url=>{if(url.endsWith('/complete')&&++completedCalls===1)throw Error('completion reply lost')});
 await q.elements.finishBtn.onclick();assert.equal(q.elements.retry.hidden,false);assert.equal(q.storage.size,1);
 await q.elements.retry.onclick();assert.equal(JSON.parse([...q.storage.values()][0]).completed,true);assert.equal(q.accepted.size,1);assert.equal(completedCalls,2);
});
test('old browser session is migrated only after server confirms owner',async()=>{
 const storage=new Map([['verifiedQuiz:A1:en',JSON.stringify({sid:'server-session',request_id:'oldrequest1234567890',position:19})]]);
 const q=await setup('en',{storage,accepted:new Map([[0,'correct']]),hook:(url,b)=>{
  if(url.endsWith('/question')&&b.position===undefined)return {ok:true,status:200,json:async()=>({status:'active',question:{user_id:'42',level:'A1',language:'en',position:0,es:'el agua',context:'',options:['correct','wrong'],accepted:true,chosen:'correct',correct:true,answer:'correct',example:'',accepted_total:1,total:20}})};
 }});
 assert.equal(q.storage.has('verifiedQuiz:A1:en'),false);assert.equal(JSON.parse(q.storage.get('verifiedQuiz:42:A1:en')).request_id,'oldrequest1234567890');assert.equal(q.elements.nextBtn.disabled,false);
});
test('progress uses server total, restores after reload, and reaches 100 percent',async()=>{
 const q=await setup('en');assert.equal(q.elements.progressAccepted.textContent,'0');assert.equal(q.elements.progressTotal.textContent,'20');
 for(let i=0;i<5;i++){await q.elements.optionsContainer.children[0].onclick();if(i<4)await q.elements.nextBtn.onclick();}
 assert.equal(q.elements.progressAccepted.textContent,'5');assert.equal(q.elements.progressFill.style.width,'25%');
 await q.open();assert.equal(q.elements.progressAccepted.textContent,'5');assert.equal(q.elements.progressBar.attributes['aria-valuenow'],'5');
 for(let i=5;i<20;i++){await q.elements.nextBtn.onclick();await q.elements.optionsContainer.children[0].onclick();}
 assert.equal(q.elements.progressFill.style.width,'100%');assert.equal(q.elements.progressBar.attributes['aria-valuemax'],'20');
});
test('progress remains last confirmed during a network error and reconciles once',async()=>{
 const q=await setup('uk');await q.elements.optionsContainer.children[0].onclick();await q.elements.nextBtn.onclick();
 q.setHook((url,b)=>{if(url.endsWith('/answer')){q.accepted.set(b.position,b.chosen);throw Error('lost reply')}});
 await q.elements.optionsContainer.children[0].onclick();assert.equal(q.elements.progressAccepted.textContent,'1');
 q.setHook(null);await q.elements.retry.onclick();assert.equal(q.elements.progressAccepted.textContent,'2');
 await q.elements.optionsContainer.children[0].onclick();assert.equal(q.elements.progressAccepted.textContent,'2');
});
for(const choice of ['correct','wrong'])test('last '+choice+' answer hides Next, retains feedback and full progress',async()=>{
 const accepted=new Map(Array.from({length:19},(_,i)=>[i,'correct']));const q=await setup('en',{accepted});
 await q.elements.nextBtn.onclick();await q.elements.optionsContainer.children[choice==='correct'?0:1].onclick();
 assert.equal(q.elements.nextBtn.hidden,true);assert.equal(q.elements.finishBtn.hidden,false);assert.equal(q.elements.finishBtn.disabled,false);
 assert.equal(q.elements.progressAccepted.textContent,'20');assert.equal(q.elements.hint.textContent,'You have answered all questions. View your result.');assert.ok(q.elements.result.textContent);
});
for(const [correct,incorrect,percent] of [[0,20,'0%'],[10,10,'50%'],[18,2,'90%'],[20,0,'100%'],[0,0,'—'],[2,1,'67%']])test('confirmed summary ring '+percent,async()=>{
 const q=await setup('en',{hook:(url)=>url.endsWith('/question')?{ok:true,status:200,json:async()=>({status:'completed',question:{position:0,es:'old',options:[],context:'',total:20,accepted_total:correct+incorrect,summary:{correct,incorrect}}})}:null});
 assert.equal(q.elements.summaryPercent.textContent,percent);assert.equal(q.elements.quizSummary.hidden,false);
 for(const id of ['questionPrompt','wordText','exampleText','optionsContainer','nextBtn','finishBtn'])assert.equal(q.elements[id].hidden,true);
 assert.equal(q.elements.summaryArc.attributes.visibility,correct===0?'hidden':'visible');
 const fraction=(correct+incorrect)?correct/(correct+incorrect):0;
 assert.ok(Math.abs(Number(q.elements.summaryArc.style.strokeDashoffset)-2*Math.PI*74*(1-fraction))<1e-8);
 assert.ok(q.elements.summaryAnswered.textContent.includes(String(correct+incorrect)));
});
test('saving label and failed completion never show a successful summary',async()=>{
 const q=await setup('uk');await q.elements.optionsContainer.children[0].onclick();let resolve;
 q.setHook(url=>url.endsWith('/complete')?new Promise(r=>resolve=r):null);
 const pending=q.elements.finishBtn.onclick();await Promise.resolve();assert.equal(q.elements.finishBtn.disabled,true);assert.equal(q.elements.finishBtn.textContent,'Зберігаємо результат…');
 resolve({ok:false,status:503,json:async()=>({error:'unavailable'})});await pending;
 assert.notEqual(q.elements.quizSummary?.hidden,false);assert.equal(q.elements.retry.hidden,false);
 q.setHook(null);await q.elements.retry.onclick();assert.equal(q.elements.quizSummary.hidden,false);
});
test('reload completed session restores summary; Return closes only Telegram app',async()=>{
 let closes=0;const tg={initData:'signed-telegram-data',platform:'ios',close(){closes++}};
 const q=await setup('en',{tg});await q.elements.optionsContainer.children[0].onclick();await q.elements.finishBtn.onclick();
 await q.open();assert.equal(q.elements.quizSummary.hidden,false);assert.equal(q.elements.returnToBot.hidden,false);
 q.elements.returnToBot.onclick();assert.equal(closes,1);assert.equal(q.storage.size,0);
 const outside=await setup('en');await outside.elements.optionsContainer.children[0].onclick();await outside.elements.finishBtn.onclick();
 assert.equal(outside.elements.returnToBot.hidden,true);assert.equal(outside.elements.returnHint.hidden,false);
});
for(const lang of ['uk','en','es','de'])test(lang+' full secure UI independent from English answers',async()=>{
 const q=await setup(lang,{translation:'en'});const dictionary=q.context.window.QuizLocales[lang];
 assert.equal(q.elements.finishBtn.textContent,dictionary.secureFinish);assert.equal(q.elements.quizTitle.textContent,dictionary.heading);
 await q.elements.optionsContainer.children[0].onclick();await q.elements.finishBtn.onclick();
 assert.equal(q.elements.summaryTitle.textContent,dictionary.summaryTitle);assert.equal(q.elements.summaryAccuracy.textContent,dictionary.accuracy);
 const create=q.calls.find(c=>c.url.endsWith('/session')).body;assert.equal(create.interface_language,lang);assert.equal(create.translation_language,'en');assert.equal(create.learning_language,'es');
});
test('all four WebApp catalogs have equal keys and placeholder contracts',async()=>{
 const q=await setup('en'),catalogs=q.context.window.QuizLocales;
 const keys=Object.keys(catalogs.uk).sort();
 for(const lang of ['uk','en','es','de']){
  assert.deepEqual(Object.keys(catalogs[lang]).sort(),keys);
  for(const key of keys){assert.ok(catalogs[lang][key].trim());assert.deepEqual([...catalogs[lang][key].matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort(),[...catalogs.uk[key].matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort());}
 }
});
