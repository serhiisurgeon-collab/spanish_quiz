"""Shared content contract; levels/review belong to the original learning language.
Stage three imports existing material with evidence instead of blindly reversing translations.
"""
LANGUAGES={'uk','en','es','de'}
STATUSES={'draft','needs_review','reviewed','excluded'}

def validate_material(record):
    required=('id','source_language','level','kind','sense','text','translations','example','review_status','grammar')
    if any(key not in record for key in required):raise ValueError('Missing material field')
    if not isinstance(record['id'],str) or not record['id'].strip():raise ValueError('Stable ID required')
    if record['source_language'] not in LANGUAGES or record['review_status'] not in STATUSES:raise ValueError('Invalid language/status')
    if record['level'] not in {'A1','A2','B1',None} or record['kind'] not in {'word','expression','poem','caption'}:raise ValueError('Invalid level/kind')
    if not isinstance(record['text'],str) or not record['text'].strip():raise ValueError('Empty original')
    for language,translation in record['translations'].items():
        if language not in LANGUAGES or language==record['source_language']:raise ValueError('Invalid target')
        if translation.get('review_status') not in STATUSES or not translation.get('text','').strip():raise ValueError('Invalid translation')
    example=record['example']
    if record['review_status']=='reviewed' and record['kind'] in {'word','expression'} and not example.get('original','').strip():raise ValueError('Example required')
    if record['source_language']=='de' and record['kind']=='word' and record['grammar'].get('part_of_speech')=='noun':
        grammar=record['grammar']
        if not grammar.get('article') or not (grammar.get('plural') or grammar.get('uncountable')):raise ValueError('German noun grammar required')
    if record['kind']=='poem':
        if record.get('original_language')!=record['source_language']:raise ValueError('Poem origin must not be relabelled')
        if record.get('rights_status') not in {'unknown','licensed','public_domain','author_permission','project_original'}:raise ValueError('Rights status required')
    if record.get('rights_status')=='project_original':
        evidence=record.get('rights_evidence',{})
        if evidence.get('origin')!='generated_in_session' or evidence.get('external_source_used') is not False or record.get('author')!='AI-generated for Spanish by Serhii':
            raise ValueError('Project original authorship evidence required')
    return record

def active_for(record,translation_language):
    validate_material(record)
    if record['review_status']!='reviewed':return False
    if record['kind']=='poem' and record['rights_status']=='unknown':return False
    translated=record['translations'].get(translation_language,{})
    if translated.get('review_status')!='reviewed':return False
    if record['kind'] in {'word','expression'} and not record['example'].get('translations',{}).get(translation_language):return False
    return True
