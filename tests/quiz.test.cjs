// Offline DOM/Telegram bridge doubles. No requests to Telegram or hosted data.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];

async function setup(level='A1', {telegram=true, error=false, sendError=false, wordsOverride, lang='uk'}={}) {
  const elements = {}, sent = [];
  function element() {
    return {textContent:'', children:[], events:{}, disabled:false,
      classList:{add(){}, remove(){}},
      addEventListener(name, callback){this.events[name]=callback},
      appendChild(child){this.children.push(child)},
      querySelectorAll(){return this.children},
      set innerHTML(value){this.children=[]},
      click(){if(!this.disabled) this.events.click()}
    };
  }
  const bridge = {expand(){}, close(){throw Error('sendData should close app')},
    sendData(data){if(sendError) throw Error('simulated bridge failure');sent.push(JSON.parse(data))}};
  const context = {URLSearchParams, TextEncoder, console:{error(){}},
    window:{location:{search:'?level='+level+'&lang='+encodeURIComponent(lang)}, ...(telegram?{Telegram:{WebApp:bridge}}:{})},
    document:{documentElement:{},getElementById(id){return elements[id]??=element()},createElement:element},
    fetch:async resource=>{
      if(error) return {ok:false,status:503};
      const words = wordsOverride || JSON.parse(fs.readFileSync(path.join(root,resource),'utf8'));
      return {ok:true,json:async()=>words};
    }};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root,'locales.js'),'utf8'),context);
  vm.runInContext(script,context);
  // Wait for the initial loadWords async chain; do not load or reset twice.
  await new Promise(setImmediate);
  function answer(correct=true) {
    const current = vm.runInContext('currentWord',context);
    const button = elements.optionsContainer.children.find(b => (b.textContent===current[vm.runInContext('lang',context)])===correct);
    assert.ok(button);
    button.click();
  }
  return {elements,sent,context,answer};
}

for(const lang of ['uk','en']) for(const level of ['A1','A2','B1','invalid']) {
  test(lang+' '+level+': render, answer once, next, and submit verified shape only on finish',async()=>{
    const q=await setup(level,{lang});
    const e=q.elements;
    assert.equal(e.error.textContent,'');
    assert.equal(e.levelBadge.textContent,(lang==='en'?'Level ':'Рівень ')+(level==='invalid'?'A1':level));
    assert.ok(e.wordText.textContent);
    assert.equal(e.finishBtn.disabled,true);
    e.finishBtn.click();assert.equal(q.sent.length,0);
    q.answer(true);
    assert.ok(e.optionsContainer.children.every(b=>b.disabled));
    // Even synthetic repeated clicks cannot change or count the answer twice.
    e.optionsContainer.children[0].events.click();
    assert.equal(vm.runInContext('answers.length',q.context),1);
    assert.equal(q.sent.length,0);
    e.nextBtn.click();q.answer(false);
    e.finishBtn.click();e.finishBtn.events.click();
    assert.equal(q.sent.length,1);
    const payload=q.sent[0];
    assert.equal(payload.answers.length,2);
    const records=JSON.parse(fs.readFileSync(path.join(root,'data',payload.level+'.json'),'utf8'));
    const target=a=>records.find(r=>r.id===a.id)[lang];
    assert.equal(payload.lang,lang);
    assert.equal(payload.answers[0].chosen,target(payload.answers[0]));
    assert.notEqual(payload.answers[1].chosen,target(payload.answers[1]));
    assert.deepEqual(Object.keys(payload.answers[0]).sort(),['chosen','id']);
    assert.equal(q.context.document.documentElement.lang,lang);
    assert.equal(payload.level,level==='invalid'?'A1':level);
  });
}

test('session stays within Telegram byte and answer limits',async()=>{
  const q=await setup('B1');
  for(let i=0;i<30;i++) {
    q.answer(true);
    if(q.elements.nextBtn.disabled) break;
    q.elements.nextBtn.click();
  }
  q.elements.finishBtn.click();
  assert.equal(q.sent.length,1);
  const payload=q.sent[0];
  assert.ok(payload.answers.length>=1&&payload.answers.length<=20);
  assert.ok(Buffer.byteLength(JSON.stringify(payload))<=3500);
});

test('long Unicode answers cannot overflow payload; previous answers remain sendable',async()=>{
  const q=await setup('A1',{wordsOverride:[{id:'long',es:'palabra',uk:'я'.repeat(300),en:'word',
    options:{uk:['я'.repeat(300),'wrong','other','third'],en:['word','wrong','other','third']}}]});
  for(let i=0;i<20;i++) {
    q.answer(true);
    if(q.elements.error.textContent) break;
    q.elements.nextBtn.click();
  }
  assert.ok(q.elements.error.textContent);
  const count=vm.runInContext('answers.length',q.context);
  q.elements.finishBtn.click();
  assert.equal(q.sent.length,1);
  assert.ok(count>0);
  assert.equal(q.sent[0].answers.length,count);
  assert.ok(Buffer.byteLength(JSON.stringify(q.sent[0]))<=3500);
});

test('fetch failure shows error and cannot submit',async()=>{
  const q=await setup('A1',{error:true});
  assert.ok(q.elements.error.textContent);
  assert.equal(q.elements.finishBtn.disabled,true);
  assert.equal(q.elements.nextBtn.disabled,true);
});

test('outside Telegram shows actionable message instead of claiming delivery',async()=>{
  const q=await setup('A1',{telegram:false});q.answer();q.elements.finishBtn.click();
  assert.equal(q.sent.length,0);
  assert.match(q.elements.error.textContent,/особистому чаті/);
});

test('synchronous send failure permits retry',async()=>{
  const q=await setup('A1',{sendError:true});q.answer();q.elements.finishBtn.click();
  assert.equal(q.sent.length,0);
  assert.equal(q.elements.finishBtn.disabled,false);
  assert.match(q.elements.error.textContent,/Спробуй ще раз/);
});

test('Telegram SDK outside a Telegram client also shows an actionable message',async()=>{
  const q=await setup();
  q.context.window.Telegram.WebApp.platform='unknown';
  q.answer();q.elements.finishBtn.click();
  assert.equal(q.sent.length,0);
  assert.match(q.elements.error.textContent,/особистому чаті/);
});


test('invalid and absent language parameters fall back to Ukrainian',async()=>{
  for(const lang of ['','fr','EN','en&premium=true']) {
    const q=await setup('A1',{lang});
    assert.equal(q.context.document.documentElement.lang,'uk');
    q.answer();q.elements.finishBtn.click();
    assert.equal(q.sent[0].lang,'uk');
  }
});

test('all question options are nonempty, unique and have exactly one correct answer in both languages',()=>{
  const normalize=s=>s.normalize('NFKC').trim().toLowerCase();
  for(const level of ['A1','A2','B1']) for(const row of JSON.parse(fs.readFileSync(path.join(root,'data',level+'.json'),'utf8'))) {
    for(const lang of ['uk','en']) {
      const options=row.options[lang];
      assert.equal(options.length,4);
      assert.ok(options.every(s=>s.trim()));
      assert.equal(new Set(options.map(normalize)).size,4);
      assert.equal(options.filter(s=>normalize(s)===normalize(row[lang])).length,1);
    }
  }
});

test('locale keys and placeholders match and English renders localized feedback',async()=>{
  const q=await setup('B1',{lang:'en'});
  const {uk,en}=q.context.window.QuizLocales;
  assert.deepEqual(Object.keys(uk).sort(),Object.keys(en).sort());
  for(const key of Object.keys(uk)) {
    const placeholders=s=>[...s.matchAll(/\{(\w+)\}/g)].map(x=>x[1]).sort();
    assert.deepEqual(placeholders(uk[key]),placeholders(en[key]));
    assert.ok(uk[key]&&en[key]);
  }
  assert.equal(q.elements.questionPrompt.textContent,en.prompt);
  assert.equal(q.elements.nextBtn.textContent,en.next);
  q.answer(false);
  assert.match(q.elements.result.textContent,/Incorrect/);
  assert.ok(q.elements.result.textContent.includes(vm.runInContext('currentWord.en',q.context)));
});

test('duplicate or blank translated options reject the entire dataset',async()=>{
  for(const options of [['word','word','x','y'],['word','','x','y']]) {
    const q=await setup('A1',{lang:'en',wordsOverride:[{id:'bad',es:'palabra',uk:'слово',en:'word',options:{en:options}}]});
    assert.match(q.elements.error.textContent,/Could not load/);
    assert.equal(q.elements.finishBtn.disabled,true);
    assert.equal(q.elements.nextBtn.disabled,true);
  }
});

test('new A1 questions show Spanish context and reveal the translated example only after answering',async()=>{
  const records=JSON.parse(fs.readFileSync(path.join(root,'data/A1.json'),'utf8'));
  const row=records.find(r=>r.es==='la cabeza');
  for(const lang of ['uk','en']) {
    const q=await setup('A1',{lang,wordsOverride:[row]});
    assert.ok(q.elements.exampleText.textContent.includes(row.example.es));
    assert.ok(!q.elements.exampleText.textContent.includes(row.example[lang]));
    assert.deepEqual(new Set(q.elements.optionsContainer.children.map(b=>b.textContent)),new Set(row.options[lang]));
    q.answer(true);
    assert.ok(q.elements.result.textContent.includes(row.example[lang]));
    q.elements.finishBtn.click();
    assert.equal(q.sent[0].answers[0].id,row.id);
    assert.equal(q.sent[0].answers[0].chosen,row[lang]);
  }
});

test('legacy ambiguous A1 words display context for their selected sense',async()=>{
  const records=JSON.parse(fs.readFileSync(path.join(root,'data/A1.json'),'utf8'));
  for(const lemma of ['mañana','piso','tierra','poder']) {
    const row=records.find(r=>r.lemma===lemma);
    const q=await setup('A1',{lang:'en',wordsOverride:[row]});
    assert.ok(q.elements.exampleText.textContent.includes(row.example.es));
    q.answer(false);
    assert.ok(q.elements.result.textContent.includes(row.en));
  }
});

test('regional usage is shown on A1 questions',async()=>{
  const row=JSON.parse(fs.readFileSync(path.join(root,'data/A1.json'),'utf8')).find(r=>r.es==='el ordenador');
  const q=await setup('A1',{lang:'en',wordsOverride:[row]});
  assert.match(q.elements.exampleText.textContent,/Usage: Spain/);
});

test('incomplete example translations cannot be loaded',async()=>{
  const row=JSON.parse(fs.readFileSync(path.join(root,'data/A1.json'),'utf8')).find(r=>r.id.startsWith('a1_'));
  delete row.example.en;
  const q=await setup('A1',{lang:'en',wordsOverride:[row]});
  assert.match(q.elements.error.textContent,/Could not load/);
  assert.equal(q.elements.finishBtn.disabled,true);
});
