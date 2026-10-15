"""Offline Chromium regression: original B1 courses on narrow mobile screens.
Run: python tests/mobile_courses.py (requires Playwright and Chromium).
All requests are intercepted, including Telegram and the API; no live calls.
"""
import json,asyncio,mimetypes
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1];runtime=json.loads((ROOT.parent/'telegram_bot/data/runtime_catalog.json').read_text())
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  for ui in ('uk','en','es','de'):
   for pair in [(a,b) for a in ('uk','en','es','de') for b in ('uk','en','es','de') if a!=b]:
    learning,target=pair
    context=await browser.new_context(viewport={'width':320,'height':812},device_scale_factor=1,is_mobile=True,has_touch=True,reduced_motion='reduce')
    await context.add_init_script("window.Telegram={WebApp:{initData:'mock-only',platform:'ios',expand(){},close(){window.closedByTest=true;}}};")
    state={'accepted':False,'completed':False};pool=runtime['questions']['B1'] if learning=='es' else runtime['courses'][learning]['questions']['B1'];word=max(pool,key=lambda w:max(map(len,w.get('text',w['es']).split())));errors=[]
    async def route_handler(route):
     u=urlparse(route.request.url)
     if u.hostname=='spanish-bot-web.onrender.com':
      path=u.path;body=route.request.post_data_json
      if path.endswith('/identity'):value={'user_id':'42'}
      elif path.endswith('/session'):value={'session_id':'mock-session'}
      elif path.endswith('/answer'):
       state['accepted']=True;state['chosen']=body['chosen'];value={'correct':body['chosen']==word[target],'answer':word[target],'example':word['example'][target]}
      elif path.endswith('/complete'):state['completed']=True;value={'answers':1,'correct':1,'incorrect':0,'total':20,'accepted_total':1}
      else:
       q={'id':word['id'],'position':0,'es':word.get('text',word['es']),'options':word['options'][target],'context':word['example'][learning],'total':20,'accepted_total':int(state['accepted']),'accepted':state['accepted'],'user_id':'42','level':'B1','interface_language':ui,'learning_language':learning,'translation_language':target,'summary':{'correct':int(state['accepted']),'incorrect':0}}
       if state['accepted']:q.update(chosen=state['chosen'],correct=True,answer=word[target],example=word['example'][target])
       value={'question':q,'status':'completed' if state['completed'] else 'active'}
      await route.fulfill(json=value);return
     if u.hostname=='telegram.org':await route.fulfill(body='',content_type='application/javascript');return
     path=ROOT/('index.html' if u.path=='/' else u.path.lstrip('/'))
     if path.name=='quiz-config.js':await route.fulfill(body="window.QuizConfig={apiBase:'https://spanish-bot-web.onrender.com'};",content_type='application/javascript');return
     if path.is_file():await route.fulfill(body=path.read_bytes(),content_type=mimetypes.guess_type(str(path))[0] or 'text/plain')
     else:await route.fulfill(status=404,body='')
    await context.route('**/*',route_handler)
    page=await context.new_page();page.on('pageerror',lambda e:errors.append(type(e).__name__))
    await page.goto(f'https://quiz.local/?api=https://spanish-bot-web.onrender.com&interface_language={ui}&lang={ui}&learning_language={learning}&translation_language={target}&level=B1')
    await page.locator('#optionsContainer button').first.wait_for()
    assert await page.locator('#error').inner_text()==''
    assert await page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    await page.get_by_role('button',name=word[target],exact=True).click()
    await page.wait_for_function("document.getElementById('progressAccepted').textContent==='1'")
    assert await page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth')
    if ui=='uk' and learning=='de' and target=='es':await page.screenshot(path=str(ROOT.parent/'artifacts/stage4-b1-de-es-mobile.png'),full_page=True)
    await page.locator('#finishBtn').click();await page.locator('#quizSummary').wait_for()
    assert await page.locator('#summaryPercent').inner_text()=='100%'
    await page.reload();await page.locator('#quizSummary').wait_for()
    await page.locator('#returnToBot').click();assert await page.evaluate('window.closedByTest===true');assert not errors,errors
    await context.close();print(ui,learning,target,'passed',flush=True)
  await browser.close();print('320 px, longest original token; 48 mobile UI/source/target combinations: no JS errors/overflow; accepted answer, summary, reload and mock close passed. All traffic intercepted; no real Telegram/API calls.')
asyncio.run(main())
