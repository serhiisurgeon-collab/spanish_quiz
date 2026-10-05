"""Offline validation of shared learning units; optional metadata is additive."""
import re
import unicodedata

LANGUAGES = ('es', 'uk', 'en')
TOPICS = ('people', 'home', 'food', 'time', 'travel', 'work', 'health',
          'weather_leisure', 'communication')
A2_TOPICS = ('daily', 'housing', 'work_study', 'travel', 'shopping',
             'cooking', 'health', 'relationships', 'services', 'past_events')
B1_TOPICS = ('work', 'education', 'travel', 'housing', 'health', 'relationships',
             'technology', 'society', 'money', 'life')


def b1_unit_key(text):
    key = a2_unit_key(text)
    return {'attractivo': 'atractivo', 'asuntos': 'asunto'}.get(key, key)


def a2_unit_key(text):
    key = unit_key(text)
    return {'abuela': 'abuelo', 'pantalones': 'pantalón', 'zapatos': 'zapato',
            'computadora': 'ordenador', 'quizá': 'quizás', 'victimas': 'víctimas'}.get(key, key)


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
    if 'a2_expansion' in source:
        a2 = group_records(source, 'A2')
        require(len(a2) >= 1000, 'A2 target not met')
        require(len({r['id'] for r in a2}) == len(a2), 'Duplicate A2 ID')
        identities = [(a2_unit_key(r['es']), r.get('sense', '')) for r in a2]
        require(len(set(identities)) == len(a2), 'A2 lemma/form duplicates')
        batches = source['a2_expansion']['batches']
        new_ids = {rid for b in batches for rid in b['ids']}
        require(all(100 <= b['count'] <= 150 and len(b['ids']) == b['count'] for b in batches),
                'Invalid A2 batch size')
        require(len(new_ids) == sum(b['count'] for b in batches) and new_ids <= known,
                'Invalid A2 batch references')
        a1_keys = {a2_unit_key(r['es']) for r in group_records(source, 'A1')}
        same_lemma = {}
        for r in a2:
            key = a2_unit_key(r['es'])
            same_lemma.setdefault(key, []).append(r)
            require(r.get('level') == 'A2' and r.get('topic') in A2_TOPICS, 'Missing A2 classification')
            require(all(isinstance(r.get(k), str) and r[k].strip() for k in LANGUAGES),
                    'Missing A2 translation')
            if r['id'] in new_ids:
                require(key not in a1_keys or bool(r.get('sense')), 'New A2 unit repeats A1')
                require(isinstance(r.get('lemma'), str) and a2_unit_key(r['lemma']) == key,
                        'Missing or inconsistent A2 lemma')
                require(r.get('type') in ('word', 'expression') and r.get('region') in ('neutral', 'ES'),
                        'Invalid new A2 metadata')
                require(r.get('part_of_speech') in ('noun', 'verb', 'other'), 'Missing A2 part of speech')
                if r['part_of_speech'] == 'noun':
                    require(bool(re.match(r'^(el|la|los|las)\s', r['es'], re.I)), 'A2 noun needs article')
                if r['part_of_speech'] == 'verb':
                    require(bool(re.search(r'(ar|er|ir|ír)(se)?$', r['es'].split()[0])),
                            'A2 verb needs infinitive')
                example = r.get('example', {})
                require(all(isinstance(example.get(k), str) and example[k].strip() for k in LANGUAGES),
                        'Missing A2 example')
                require(not any('\u0400' <= c <= '\u04ff' for c in r['es']+r['en']+example['es']+example['en']),
                        'Unexpected Cyrillic in A2')
        for rows in same_lemma.values():
            if len(rows) > 1:
                require(all(r.get('sense') and all(r.get('example', {}).get(k, '').strip() for k in LANGUAGES)
                            for r in rows), 'A2 different senses need explicit context')
                require(all(len({r[lang] for r in rows}) == len(rows) for lang in ('uk', 'en')),
                        'A2 senses need distinct translations')
    if 'b1_expansion' in source:
        active = group_records(source, 'B1')
        require(len(active) >= 1500, 'B1 target not met')
        require(len({r['id'] for r in active}) == len(active), 'Duplicate B1 ID')
        identities = [(b1_unit_key(r['es']), r.get('sense', '')) for r in active]
        require(len(set(identities)) == len(active), 'B1 lemma/form duplicates')
        info = source['b1_expansion']
        new_ids = {rid for b in info['batches'] for rid in b['ids']}
        require(len(new_ids) == sum(b['count'] for b in info['batches']) and new_ids <= known,
                'Invalid B1 batch references')
        require(all(100 <= b['count'] <= 150 and len(b['ids']) == b['count'] for b in info['batches']),
                'Invalid B1 batch size')
        lower = {b1_unit_key(r['es']) for g in ('A1', 'A2') for r in group_records(source, g)}
        same_lemma = {}
        for r in active:
            same_lemma.setdefault(b1_unit_key(r['es']), []).append(r)
            if r['id'] not in new_ids:
                continue
            key = b1_unit_key(r['es'])
            require(key not in lower or bool(r.get('sense')), 'New B1 unit repeats A1/A2')
            require(r.get('level') == 'B1' and r.get('topic') in B1_TOPICS, 'Missing B1 classification')
            require(r.get('type') in ('word', 'expression'), 'Invalid B1 type')
            require(isinstance(r.get('lemma'), str) and b1_unit_key(r['lemma']) == key, 'Invalid B1 lemma')
            require(r.get('register') in ('neutral', 'formal', 'colloquial'), 'Missing B1 register')
            require(r.get('region') in ('neutral', 'ES'), 'Invalid B1 region')
            require(r.get('part_of_speech') in ('noun', 'verb', 'other'), 'Missing B1 part of speech')
            if r['part_of_speech'] == 'noun':
                require(bool(re.match(r'^(el|la|los|las)\s', r['es'], re.I)), 'B1 noun needs article')
            if r['part_of_speech'] == 'verb':
                tokens = r['es'].split()
                verb = tokens[1] if tokens[0] == 'no' and len(tokens) > 1 else tokens[0]
                require(bool(re.search(r'(ar|er|ir|ír)(se)?$', verb)), 'B1 verb needs infinitive')
            example = r.get('example', {})
            require(all(isinstance(example.get(k), str) and example[k].strip() for k in LANGUAGES),
                    'Missing B1 example')
            require(not any('\u0400' <= c <= '\u04ff' for c in r['es']+r['en']+example['es']+example['en']),
                    'Unexpected Cyrillic in B1')
            if r.get('sense'):
                require(bool(example['es']), 'New B1 sense needs context')
        for rows in same_lemma.values():
            if len(rows) > 1:
                require(all(r.get('sense') and all(r.get('example', {}).get(k, '').strip() for k in LANGUAGES)
                            for r in rows), 'B1 different senses need explicit context')
                require(all(len({r[lang] for r in rows}) == len(rows) for lang in ('uk', 'en')),
                        'B1 senses need distinct translations')
