// Offline DOM/Telegram bridge doubles. No requests to Telegram or hosted data.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)][0][1];

async function setup(level='A1', {telegram=true, error=false, sendError=false, wordsOverride}={}) {
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
    window:{location:{search:'?level='+level}, ...(telegram?{Telegram:{WebApp:bridge}}:{})},
    document:{getElementById(id){return elements[id]??=element()},createElement:element},
    fetch:async resource=>{
      if(error) return {ok:false,status:503};
      const words = wordsOverride || JSON.parse(fs.readFileSync(path.join(root,resource),'utf8'));
      return {ok:true,json:async()=>words};
    }};
  vm.createContext(context);
  vm.runInContext(script,context);
  // Wait for the initial loadWords async chain; do not load or reset twice.
  await new Promise(setImmediate);
  function answer(correct=true) {
    const current = vm.runInContext('currentWord',context);
    const button = elements.optionsContainer.children.find(b => (b.textContent===current.uk)===correct);
    assert.ok(button);
    button.click();
  }
  return {elements,sent,context,answer};
}

for(const level of ['A1','A2','B1','invalid']) {
  test(level+': render, answer once, next, and submit verified shape only on finish',async()=>{
    const q=await setup(level);
    const e=q.elements;
    assert.equal(e.error.textContent,'');
    assert.equal(e.levelBadge.textContent,'Level '+(level==='invalid'?'A1':level));
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
    assert.equal(payload.answers[0].chosen,payload.answers[0].translation);
    assert.notEqual(payload.answers[1].chosen,payload.answers[1].translation);
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
  const q=await setup('A1',{wordsOverride:[{es:'palabra',uk:'я'.repeat(300),options:['я'.repeat(300),'wrong']}]});
  q.answer(true);q.elements.nextBtn.click();q.answer(true);
  q.elements.nextBtn.click();q.answer(true);
  assert.ok(q.elements.error.textContent);
  q.elements.finishBtn.click();
  assert.equal(q.sent.length,1);
  assert.equal(q.sent[0].answers.length,2);
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
