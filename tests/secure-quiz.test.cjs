const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
async function setup(lang='uk',bad=false){
 const elements={},calls=[],storage=new Map();
 function element(){return {textContent:'',children:[],disabled:false,classList:{add(){}},appendChild(x){this.children.push(x)},querySelectorAll(){return this.children},set innerHTML(x){this.children=[]}}}
 const context={URLSearchParams,crypto:{randomUUID:()=> 'request1234567890'},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},window:{QuizConfig:{apiBase:'https://api.example'}},document:{documentElement:{},getElementById:id=>elements[id]??=element(),createElement:element},fetch:async(url,options)=>{
  const body=JSON.parse(options.body);calls.push({url,body});
  if(url.endsWith('/session'))return {ok:true,json:async()=>({session_id:'server-session'})};
  if(url.endsWith('/question'))return {ok:true,json:async()=>({status:'active',question:{id:'stable',es:'el agua',context:'Bebo agua.',options:['correct','wrong','other','fourth']}})};
  if(url.endsWith('/answer'))return {ok:true,json:async()=>({correct:body.chosen==='correct',answer:'correct',example:'Translated example'})};
  return {ok:true,json:async()=>({correct:1,incorrect:0})};
 }};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'locales.js'),'utf8'),context);vm.runInContext(fs.readFileSync(path.join(root,'secure-quiz.js'),'utf8'),context);
 await context.window.startSecureQuiz({initData:'signed-telegram-data'},new URLSearchParams({api:bad?'https://evil.example':'https://api.example',lang,level:'A1'}));
 return {elements,calls,storage};
}
for(const lang of ['uk','en'])test(lang+' secure mode accepts server results, no local scores or duplicate answer',async()=>{
 const q=await setup(lang),e=q.elements;
 assert.equal(q.calls.length,2);assert.equal(e.exampleText.textContent.includes('Translated example'),false);
 await e.optionsContainer.children[0].onclick();await e.optionsContainer.children[0].onclick();
 const answer=q.calls.filter(c=>c.url.endsWith('/answer'));assert.equal(answer.length,1);
 assert.equal(answer[0].body.session_id,'server-session');assert.equal(answer[0].body.chosen,'correct');
 assert.equal('correct' in answer[0].body,false);assert.equal('telegram_id' in answer[0].body,false);
 assert.ok(e.exampleText.textContent.includes('Translated example'));
 await e.finishBtn.onclick();assert.equal(q.calls.filter(c=>c.url.endsWith('/complete')).length,1);assert.equal(q.storage.size,0);
});
test('untrusted API URL receives no initData or requests',async()=>{
 const q=await setup('en',true);assert.equal(q.calls.length,0);assert.ok(q.elements.error.textContent);
});
