"""Offline validation of shared learning units; optional metadata is additive."""
import re
import unicodedata

LANGUAGES = ('es', 'uk', 'en')
TOPICS = ('people', 'home', 'food', 'time', 'travel', 'work', 'health',
          'weather_leisure', 'communication')


def unit_key(text):
    text = unicodedata.normalize('NFKC', text).casefold().strip()
    text = re.sub(r'^(el|la|los|las)\s+', '', text)
    text = re.sub(r'[¿?¡!.,;:]', '', text)
    text = ' '.join(text.split())
    return {'hermana': 'hermano', 'hija': 'hijo'}.get(text, text)


def group_records(source, group):
    records = {r['id']: r for r in source['records']}
    overrides = source.get('group_metadata', {}).get(group, {})
    return [{**records[rid], **overrides.get(rid, {})} for rid in source['groups'][group]]


def require(condition, description):
    if not condition:
        raise ValueError(description)


def validate_source(source):
    rows = source['records']
    ids = [r['id'] for r in rows]
    require(len(ids) == len(set(ids)), 'Duplicate learning ID')
    known = set(ids)
    require(set(source['groups']) == {'base', 'A1', 'A2', 'B1'}, 'Invalid groups')
    for group, members in source['groups'].items():
        require(all(rid in known for rid in members), 'Unknown ID in '+group)
    for r in rows:
        require(all(isinstance(r.get(k), str) and r[k].strip() for k in ('id', *LANGUAGES)),
                'Missing translation: '+r['id'])
        if r['id'].startswith('a1_'):
            require(r.get('level') == 'A1' and r.get('topic') in TOPICS, 'Invalid A1 classification')
            require(r.get('type') in ('word', 'expression'), 'Invalid unit type')
            require(isinstance(r.get('lemma'), str) and r['lemma'].strip(), 'Missing lemma')
            require(r.get('region') in ('neutral', 'ES'), 'Unknown region')
            require(r.get('part_of_speech') in ('noun', 'verb', 'other'), 'Missing part of speech')
            if r['part_of_speech'] == 'noun':
                require(bool(re.match(r'^(el|la|los|las)\s', r['es'], re.I)), 'Noun needs article')
            if r['part_of_speech'] == 'verb':
                require(bool(re.search(r'(ar|er|ir|ír)(se)?$', r['es'])), 'Verb needs infinitive')
            example = r.get('example', {})
            require(all(isinstance(example.get(k), str) and example[k].strip() for k in LANGUAGES),
                    'Missing example: '+r['id'])
            require(not any('\u0400' <= c <= '\u04ff' for c in r['en']+example['es']+example['en']),
                    'Unexpected Cyrillic outside Ukrainian')
    for group, overrides in source.get('group_metadata', {}).items():
        require(group in source['groups'] and set(overrides) <= set(source['groups'][group]),
                'Unknown metadata reference')
    if 'a1_expansion' in source:
        a1 = group_records(source, 'A1')
        keys = [unit_key(r.get('lemma', r['es'])) for r in a1]
        require(len(a1) >= 600, 'A1 target not met')
        require(len(set(keys)) == len(keys), 'A1 lemma/form duplicates')
        require(len({unit_key(r['es']) for r in a1}) == len(a1), 'A1 article/spelling duplicates')
        new_a1_ids = {rid for b in source['a1_expansion']['batches'] for rid in b['ids']}
        for r in a1:
            require(all(isinstance(r.get(k), str) and r[k].strip() for k in LANGUAGES), 'Empty A1 translation')
            require(r.get('level') == 'A1' and r.get('topic') in TOPICS, 'Missing A1 metadata')
            require('example' in r and all(r['example'].get(k, '').strip() for k in LANGUAGES),
                    'Incomplete A1 context')
            if r['id'] in new_a1_ids:
                require(r.get('type') in ('word', 'expression') and r.get('region') in ('neutral', 'ES'),
                        'Missing new A1 classification')
                require(r.get('part_of_speech') in ('noun', 'verb', 'other'), 'Missing new A1 part of speech')
                if r['part_of_speech'] == 'noun':
                    require(bool(re.match(r'^(el|la|los|las)\s', r['es'], re.I)), 'A1 noun needs article')
                if r['part_of_speech'] == 'verb':
                    require(bool(re.search(r'(ar|er|ir|ír)(se)?$', r['es'])), 'A1 verb needs infinitive')
        batches = source['a1_expansion']['batches']
        require(all(100 <= b['count'] <= 150 and len(b['ids']) == b['count'] for b in batches),
                'Invalid batch size')
        require(all(rid in known for b in batches for rid in b['ids']), 'Unknown batch ID')
        require(len({rid for b in batches for rid in b['ids']}) == sum(b['count'] for b in batches),
                'Duplicate candidate across batches')
