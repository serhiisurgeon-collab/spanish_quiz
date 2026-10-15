"""Compile reviewed Spanish content and conservative, audited distractor banks.
Legacy sources/snapshots are never modified. Only this projection is served.
"""
import random,re,unicodedata

def norm(s):
    return ' '.join(unicodedata.normalize('NFKC',s).casefold().replace('ʼ',"'").replace('’',"'").split())

def plain(s):
    return re.sub(r'\s*\([^)]*\)','',norm(s)).strip(' .!?')

# Closed bank of mutually distinct concrete meanings. Matching/contained historical
# translations are excluded too (e.g. Kissen vs Sofakissen, school vs secondary school).
NOUNS=('agua','pan','ventana','lunes','avión','cuchillo','queso','contraseña','antibiótico','biblioteca','kilómetro','zoológico','gasolina','almohada','embajada','cascada','cementerio','arqueología','cadera','botella')
# Whole verb phrases, not unrelated noun options for multiword questions.
PHRASES=('pedir cita médica','perder un vuelo','cocinar al vapor','pagar en efectivo','alquilar un coche','renovar un contrato laboral','aprender por cuenta propia','poner una inyección','reclamar una maleta perdida','instalar un detector de humo','plantar árboles','cambiar de sector')
VERBS=('dormir','comprar','leer','escribir','beber','comer','nadar','correr','conducir','bailar','vender','abrir')
ADJECTIVES=('rojo','azul','grande','pequeño','caro','barato','frío','caliente','abierto','cerrado','peligroso','seguro')
CONNECTORS=('Sin embargo','Por lo tanto','Debido a','al principio','por primera vez','En caso de que','Según me contó')

def compile_runtime(data):
    from content_contract import active_for
    rows={r['id']:r for r in data['records']}
    def view(r,group):
        old=r.get('legacy_views',{}).get(group,r['legacy']);v=dict(old)
        v.update(id=r['id'],canonical_id=r['canonical_id'],es=r['text'],sense=old.get('sense') or r['sense'],level=group if group in ('A1','A2','B1') else r['level'],source_language=r['source_language'])
        v.update({lang:r['translations'][lang]['text'] for lang in ('uk','en','de')})
        v['example']={'es':r['example']['original'],**r['example']['translations']}
        if r.get('regional_notes'):v['regional_note']={**v.get('regional_note',{}),**r['regional_notes']}
        return v
    words={g:[view(rows[rid],g) for rid in ids if all(active_for(rows[rid],l) for l in ('uk','en','de'))] for g,ids in data['groups'].items()}
    active=[r for r in rows.values() if r['kind'] in ('word','expression') and all(active_for(r,l) for l in ('uk','en','de'))]
    def lemma(r):return re.sub(r'^(el|la|los|las) ','',r['text'].casefold())
    # Explicit stable anchor selection; no unsupported/unreviewed candidate can enter.
    nouns=[next(r for r in active if lemma(r)==term) for term in NOUNS]
    def anchors(terms):return [next(r for r in active if lemma(r)==term.casefold()) for term in terms]
    phrases=anchors(PHRASES);verbs=anchors(VERBS);adjectives=anchors(ADJECTIVES);connectors=anchors(CONNECTORS)
    aliases={r['id']:r['canonical_id'] for r in rows.values() if r['id']!=r['canonical_id']}
    from collections import defaultdict
    by_lemma=defaultdict(list);by_identity=defaultdict(list)
    for r in active:by_lemma[lemma(r)].append(r);by_identity[r['canonical_id']].append(r)
    questions={};audit=[]
    for level in ('A1','A2','B1'):
        output=[];seen=set()
        for w in words[level]:
            if w['canonical_id'] in seen:continue
            seen.add(w['canonical_id']);r=rows[w['id']];options={};option_ids={}
            same_lemma=by_lemma[lemma(r)]+by_identity[r['canonical_id']]
            for lang in ('uk','en','de'):
                accepted={plain(x['translations'][lang]['text']) for x in same_lemma}
                for variant in r.get('legacy_views',{}).values():
                    if variant.get(lang):accepted.add(plain(variant[lang]))
                candidates=[]
                # Expressions get plausible grammatical phrase alternatives;
                # word headwords use the closed concrete-noun bank.
                pos=r['grammar'].get('part_of_speech','')
                if pos in ('verb','verb_phrase') or r['legacy'].get('part_of_speech')=='verb' or r['translations']['en']['text'].startswith('to '):bank=phrases if r['kind']=='expression' else verbs
                elif pos in ('adjective','adj') or r['legacy'].get('part_of_speech')=='adjective':bank=adjectives
                elif pos in ('discourse_expression','adverbial_phrase'):bank=connectors
                else:bank=nouns
                for x in bank:
                    candidate=plain(x['translations'][lang]['text'])
                    if x['canonical_id']==r['canonical_id'] or lemma(x)==lemma(r):continue
                    if any(candidate==a or candidate in a or a in candidate for a in accepted if a):continue
                    # Phrase synonyms/near paraphrases sharing a semantic stem are unsafe.
                    source_tokens=set(re.findall(r'\w{4,}',lemma(r)))
                    if source_tokens.intersection(re.findall(r'\w{4,}',lemma(x))):continue
                    # Shared English semantic stems are conservative exclusions across
                    # target languages, catching paraphrases with different spelling.
                    def stems(text):
                        synonyms={'costly':'expensive','cheap':'inexpensive','purchase':'buy','acquire':'buy','purchas':'buy','automobil':'car','scarlet':'red','crimson':'red','secure':'safe','danger':'dangerous','aircraft':'plane','aeroplane':'plane','cushion':'pillow','gasoline':'petrol','fuel':'petrol','bathe':'swim','jog':'run','unlock':'open','begin':'open','start':'open','silent':'quiet','tiny':'small','little':'small','large':'big','quick':'fast','rapid':'fast'}
                        stop={'the','and','for','our','his','her','its','you','are','was','were','has','had','not','can','may','all','own','with','from','into','that','this','ones','one','some','have','make','take','being','something','someone','another','before','after','during','through'}
                        return {synonyms.get(t,t) for t in re.findall(r'\w{3,}',plain(text)) if t not in stop}
                    if stems(r['translations']['en']['text']) & stems(x['translations']['en']['text']):continue
                    causal={'debido a','ya que','porque','a causa de'}
                    result={'por eso','por lo tanto','así que','por tanto'}
                    contrast={'sin embargo','en cambio','aun así','no obstante','pero','a pesar de'}
                    for family in (causal,result,contrast):
                        if lemma(r) in family and lemma(x) in family:break
                    else:
                        candidates.append(x)

                rng=random.Random(w['id']+lang);rng.shuffle(candidates)
                selected=[];used={plain(w[lang])}
                for x in candidates:
                    text=x['translations'][lang]['text']
                    if plain(text) in used:continue
                    selected.append((text,x['id']));used.add(plain(text))
                    if len(selected)==3:break
                if len(selected)!=3:raise ValueError('Insufficient reviewed distractors: '+w['id']+lang)
                choices=[w[lang],*[text for text,_ in selected]];rng.shuffle(choices)
                options[lang]=choices;option_ids[lang]=[rid for _,rid in selected]
            output.append({**w,'options':options})
            audit.append({'id':w['id'],'level':level,'distractor_ids':option_ids,'policy':'closed distinct-meaning banks; canonical/same-lemma/all historical translations and contained paraphrases excluded; original-language example disambiguates meaning'})
        questions[level]=output
    content={};lookup={}
    for group,ids in data['content_groups'].items():
        entries=[]
        for rid in ids:
            r=rows[rid]
            if not all(active_for(r,l) for l in ('uk','en','de')):continue
            item={'id':rid,'canonical_id':r['canonical_id'],'es':r['text'],'legacy_uk':r['legacy']['uk']}
            for lang in ('uk','en','de'):
                item[lang]=r['text']+'\n\n'+r['translations'][lang]['text']
                lookup[item[lang]]=r['canonical_id']
            for text in r['legacy'].values():lookup[text]=r['canonical_id']
            entries.append(item)
        content[group]=entries
    return {'schema_version':1,'words':words,'questions':questions,'content':content,'content_lookup':lookup,'aliases':aliases},audit
