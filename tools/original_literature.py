"""Compile original poetry/captions without changing historical Spanish authorship."""
from content_contract import active_for
from original_courses import LANGUAGES,normalized

def compile_literature(document,courses):
    seen=set();originals=set();lookup={}
    for r in document['records']:
        rid=r['id'];src=r['source_language'];level=r['level'];kind=r['kind']
        if rid in seen:raise ValueError('Duplicate literature ID')
        seen.add(rid)
        key=(src,normalized(r['text']))
        if key in originals:raise ValueError('Duplicate literature original')
        originals.add(key)
        if src not in courses or kind not in ('poem','caption'):raise ValueError('Invalid literature course/kind')
        if r['canonical_id']!=rid or r['curriculum_levels']!={src:[] if level is None else [level]}:raise ValueError('Invalid literature identity')
        if kind=='poem' and level not in ('A1','A2','B1'):raise ValueError('Poem level required')
        if kind=='caption' and level is not None:raise ValueError('Caption must not invent a level')
        if r.get('rights_status') not in {'project_original','author_permission','licensed','public_domain'}:raise ValueError('Known literature rights required')
        targets=[lang for lang in LANGUAGES if lang!=src]
        if not all(active_for(r,lang) for lang in targets):raise ValueError('Unreviewed or unlicensed literature')
        item={'id':rid,'canonical_id':rid,'legacy_uk':rid,'source_language':src,'text':r['text'],
              'project_original':r.get('rights_status')=='project_original'}
        for target in targets:
            item[target]=r['text']+'\n\n'+r['translations'][target]['text']
            lookup[item[target]]=rid
        lookup[rid]=rid
        content=courses[src]['content']
        for group in ('POEMS_BASE','POEMS_A1','POEMS_A2','POEMS_B1','CAPTIONS'):content.setdefault(group,[])
        group='CAPTIONS' if kind=='caption' else 'POEMS_'+level
        content[group].append(item)
        if kind=='poem' and level=='A1':content['POEMS_BASE'].append(item)
    return lookup
