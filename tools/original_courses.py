"""Compile explicitly authored original-language courses, never reversed legacy glosses."""
import random
import unicodedata
from content_contract import active_for, validate_material

LANGUAGES=('uk','en','es','de')

def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC',value).casefold().split())

def compile_courses(document):
    records=document['records'];by_id={r['id']:r for r in records}
    if len(by_id)!=len(records):raise ValueError('Duplicate original-course ID')
    seen=set();courses={};audit=[]
    for r in records:
        validate_material(r)
        src=r['source_language'];level=r['level']
        key=(src,normalized(r['text']),r['sense'])
        if key in seen:raise ValueError('Duplicate original meaning')
        seen.add(key)
        if r['canonical_id']!=r['id'] or r['curriculum_levels']!={src:[level]}:raise ValueError('Invalid original curriculum identity')
        targets=[l for l in LANGUAGES if l!=src]
        if not all(active_for(r,l) for l in targets):raise ValueError('Unreviewed original-course record')
        view={'id':r['id'],'canonical_id':r['canonical_id'],'source_language':src,'text':r['text'],src:r['text'],
              **{l:r['translations'][l]['text'] for l in targets},'example':{src:r['example']['original'],**r['example']['translations']},
              'level':level,'sense':r['sense'],'grammar':r['grammar'],'topic':r['topic']}
        options={}
        ids=r['distractor_ids']
        if len(ids)!=3 or len(set(ids))!=3 or r['id'] in ids:raise ValueError('Three distinct wrong meanings required')
        for target in targets:
            alternatives=[]
            for rid in ids:
                wrong=by_id[rid]
                if wrong['source_language']!=src or wrong['level']!=level or wrong['sense']==r['sense']:raise ValueError('Invalid distractor source')
                alternatives.append(wrong['translations'][target]['text'])
            choices=[view[target],*alternatives]
            if len({normalized(c) for c in choices})!=4:raise ValueError('Duplicate translated options')
            random.Random(r['id']+target).shuffle(choices);options[target]=choices
        course=courses.setdefault(src,{'words':{'base':[],'A1':[],'A2':[],'B1':[]},'questions':{'A1':[],'A2':[],'B1':[]},'content':{}})
        course['words'][level].append(view)
        if level=='A1':course['words']['base'].append(view)
        course['questions'][level].append({**view,'options':options})
        audit.append({'id':r['id'],'source_language':src,'level':level,'distractor_ids':ids,'policy':'Individually reviewed, semantically distinct quartets of the same grammatical class; no client grading'})
    for src,expected in document['coverage'].items():
        for level,count in expected.items():
            if len(courses[src]['words'][level])!=count:raise ValueError('Coverage mismatch')
    return courses,audit
