"""Lossless deterministic import. Unproven linguistic/rights quality stays needs_review."""
import argparse
import hashlib
import json
import re
from collections import Counter,defaultdict
from pathlib import Path
from content_contract import validate_material
from learning_schema import group_records

ROOT=Path(__file__).resolve().parents[1]

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def migrate(source,content,patches,reviews=None,rights=None):
    reviews=reviews or {}
    rights=rights or {}
    views=defaultdict(dict)
    for group in source['groups']:
        for row in group_records(source,group):views[row['id']][group]=row
    records=[];issues=[]
    for old in source['records']:
        variants=views[old['id']]
        # A1 first: every active A1 entry already has an explicit example/context.
        chosen=variants.get('A1') or variants.get('A2') or variants.get('B1') or old
        memberships=list(variants)
        example=chosen.get('example',{})
        translations={lang:dict(text=chosen[lang],review_status='needs_review') for lang in ('uk','en')}
        record=dict(id=old['id'],source_language='es',level=chosen.get('level') or next((g for g in memberships if g!='base'),None),kind=chosen.get('type','expression' if ' ' in chosen['es'].strip() and not re.match(r'^(el|la|los|las)\s',chosen['es']) else 'word'),sense=chosen.get('sense') or '',text=chosen['es'],translations=translations,example=dict(original=example.get('es',''),translations={lang:example[lang] for lang in ('uk','en') if example.get(lang)}),review_status='needs_review',grammar=dict(part_of_speech=chosen.get('part_of_speech','unknown'),lemma=chosen.get('lemma',chosen['es'])),curriculum_levels={'es':[g for g in memberships if g!='base']},memberships=memberships,legacy=old,legacy_views=variants,provenance=dict(kind='legacy_import',source_id=old['id'],source_digest=digest(old)),issues=[])
        if not example.get('es'):record['issues'].append('missing_original_example')
        if len({(v['es'],v['uk'],v['en']) for v in variants.values()})>1:record['issues'].append('different_legacy_views_require_semantic_review')
        if not memberships:record['review_status']='excluded';record['issues'].append('archived_not_in_active_groups')
        if old['id'] in patches:
            patch=patches[old['id']]
            record['translations']['de']=dict(text=patch['de'],grammar=patch.get('grammar',{}),review_status='needs_review')
            record['issues'].append('german_gloss_requires_context_and_example_review')
        if old['id'] in reviews:
            review=reviews[old['id']]
            record.update(review)
            record['issues']=['legacy_views_preserved_separately'] if variants else []
        validate_material(record);records.append(record)
        if record['issues']:issues.append(dict(id=record['id'],issues=record['issues']))
    poetry=[];groups={};by_id={}
    for group,rows in content.items():
        groups[group]=[]
        for row in rows:
            original,separator,target=row['uk'].partition('\n\n')
            en_original,en_separator,en_target=row['en'].partition('\n\n')
            if not separator or not en_separator or original!=en_original:raise ValueError('Unresolved bilingual content split')
            kind='caption' if group=='CAPTIONS' else 'poem'
            # Exact existing canonical identity used by weekly deliveries. No positional IDs.
            rid=('caption_' if kind=='caption' else 'poem_')+hashlib.sha256(row['uk'].encode()).hexdigest()
            if rid not in by_id:
                entry=dict(id=rid,source_language='es',original_language='es',level=None,kind=kind,sense='',text=original,translations={'uk':{'text':target,'review_status':'needs_review'},'en':{'text':en_target,'review_status':'needs_review'}},example={'original':'','translations':{}},review_status='needs_review',grammar={},rights_status='unknown',author=None,attribution=None,curriculum_levels={'es':[]},legacy=row,memberships=[],issues=['rights_and_authorship_unverified' if kind=='poem' else 'factual_caption_requires_verification'])
                if kind=='poem' and rid in rights:
                    entry.update(rights[rid])
                    entry['issues']=['poem_translations_require_review']
                by_id[rid]=entry;poetry.append(entry)
            entry=by_id[rid];entry['memberships'].append(group)
            if group.startswith('POEMS_') and group!='POEMS_BASE':entry['curriculum_levels']['es'].append(group[-2:])
            groups[group].append(rid);validate_material(entry)
    result=dict(schema_version=2,source_digests={'vocabulary':digest(source),'content':digest(content)},records=records+poetry,groups=source['groups'],content_groups=groups,legacy_source=source,legacy_content=content,import_policy='needs_review unless independently verified; original-language levels only')
    report=dict(vocabulary_records=len(records),poem_records=sum(r['kind']=='poem' for r in poetry),caption_records=sum(r['kind']=='caption' for r in poetry),duplicate_memberships={g:len(ids)-len(set(ids)) for g,ids in source['groups'].items()},statuses=dict(Counter(r['review_status'] for r in result['records'])),german_draft_glosses=len(patches)-sum(rid in reviews for rid in patches),reviewed_source_units=len(reviews),missing_original_examples=sum('missing_original_example' in r['issues'] for r in records),differing_views=sum('different_legacy_views_require_semantic_review' in r['issues'] for r in records),review_queue=issues)
    return result,report

def main():
    p=argparse.ArgumentParser();p.add_argument('--bot-root',type=Path,default=ROOT.parent/'telegram_bot');p.add_argument('--check',action='store_true');args=p.parse_args()
    source=json.loads((ROOT/'data/learning.json').read_text());content=json.loads((args.bot_root/'locales/content.json').read_text());patches=json.loads((ROOT/'data/german_gloss_drafts.json').read_text())
    reviews=json.loads((ROOT/'data/content_review_overrides.json').read_text())
    data,report=migrate(source,content,patches,reviews,json.loads((ROOT/'data/content_rights.json').read_text()))
    outputs={ROOT/'data/materials_v2.json':data,args.bot_root/'data/materials_v2.json':data,ROOT/'data/content_migration_audit.json':report}
    for path,value in outputs.items():
        text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
        if args.check:
            if not path.exists() or path.read_text()!=text:raise ValueError('Stale migrated artifact: '+str(path))
        else:path.write_text(text)
    print(json.dumps({k:v for k,v in report.items() if k!='review_queue'},ensure_ascii=False))
if __name__=='__main__':main()
