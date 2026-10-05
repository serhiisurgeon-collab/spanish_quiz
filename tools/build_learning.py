"""Generate deployable bot/quiz data from learning.json; never edit outputs.

Run with both checkouts present; --check verifies files without writing.
No network, credentials, or changes to Google Sheets are involved.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import random
import unicodedata
from learning_schema import group_records, unit_key, a2_unit_key, b1_unit_key, validate_source

ROOT = Path(__file__).resolve().parents[1]


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def artifacts(source, bot_root):
    validate_source(source)
    records = {r['id']: r for r in source['records']}
    assert len(records) == len(source['records']), 'Duplicate IDs'
    for r in records.values():
        assert all(isinstance(r.get(k), str) and r[k].strip() for k in ('id', 'es', 'uk', 'en'))
    assert set(source['groups']) == {'base', 'A1', 'A2', 'B1'}
    outcomes = {bot_root / 'data' / 'learning.json': source}
    # A conservative bank of distinct meanings avoids synonymous distractors.
    # All items already exist in the learning database; no vocabulary is added.
    bank_es = ['agua', 'pan', 'ventana', 'dinero', 'lunes', 'escuela', 'avión',
               'cuchillo', 'queso', 'contraseña', 'antibiótico', 'biblioteca',
               'kilómetro', 'zoológico', 'gasolina', 'almohada', 'embajada',
               'cascada', 'cementerio', 'arqueología', 'cadera', 'botella']
    meanings = defaultdict(lambda: {'uk': set(), 'en': set()})
    for r in records.values():
        for lang in ('uk', 'en'):
            meanings[normalized(r['es'])][lang].add(normalized(r[lang]))
    a1_meanings = defaultdict(lambda: {'uk': set(), 'en': set()})
    for r in [*records.values(), *group_records(source, 'A1')]:
        for lang in ('uk', 'en'):
            a1_meanings[unit_key(r['es'])][lang].add(normalized(r[lang]))
    a2_meanings = defaultdict(lambda: {'uk': set(), 'en': set()})
    for r in [*records.values(), *group_records(source, 'A2')]:
        for lang in ('uk', 'en'):
            a2_meanings[a2_unit_key(r['es'])][lang].add(normalized(r[lang]))
    b1_meanings = defaultdict(lambda: {'uk': set(), 'en': set()})
    for r in [*records.values(), *group_records(source, 'B1')]:
        for lang in ('uk', 'en'):
            b1_meanings[b1_unit_key(r['es'])][lang].add(normalized(r[lang]))
    for level in ('A1', 'A2', 'B1'):
        questions = []
        # Distractors stay within this level's existing vocabulary.
        active = group_records(source, level)
        meaning_key_for = unit_key if level == 'A1' else a2_unit_key if level == 'A2' else b1_unit_key
        level_meanings = a1_meanings if level == 'A1' else a2_meanings if level == 'A2' else b1_meanings
        bank_key = meaning_key_for
        # Money is too broad a distractor for cash/balance/payment vocabulary.
        bank = [r for r in active if bank_key(r['es']) in bank_es
                and not (level == 'A2' and bank_key(r['es']) == 'dinero')]
        for r in active:
            rid = r['id']
            output = dict(r)
            options = {}
            for lang in ('uk', 'en'):
                answer = r[lang]
                meaning_key = meaning_key_for(r['es'])
                valid_meanings = level_meanings[meaning_key][lang]
                candidates = [x[lang] for x in bank
                    if normalized(x[lang]) not in valid_meanings
                    and meaning_key_for(x['es']) != meaning_key]
                # Select fixed, reproducible options independently of UI language.
                rng = random.Random(rid + lang)
                rng.shuffle(candidates)
                choices = [answer]
                for candidate in candidates:
                    if normalized(candidate) not in {normalized(x) for x in choices}:
                        choices.append(candidate)
                    if len(choices) == 4:
                        break
                assert len(choices) == 4 and len({normalized(x) for x in choices}) == 4
                assert sum(normalized(x) == normalized(answer) for x in choices) == 1
                assert not any(normalized(x) in valid_meanings for x in choices[1:])
                rng.shuffle(choices)
                options[lang] = choices
            output['options'] = options
            questions.append(output)
        outcomes[ROOT / 'data' / (level + '.json')] = questions
    return outcomes


def report(source):
    records = {r['id']: r for r in source['records']}
    lines = ['# Аудит навчальної бази', '',
        f"Перекладено {len(records)} унікальних пар es/uk. Входжень у списках: "
        f"{sum(map(len, source['groups'].values()))}.", '',
        ('Базовий список збережено; A1, A2 та B1 очищено й розширено (див. звіти *_EXPANSION.md).'
         if 'a1_expansion' in source else 'Порядок, повтори, іспанські оригінали й українські переклади збережено.'),
        'Початкові записи лишаються у джерелі. Кілька перекладів одного es можуть бути синонімами,',
        'різними значеннями або старими неточностями; їх не виправлено мовчки.', '',
        '## Точні повтори всередині списків', '', '| Список | es | uk | Кількість |', '|---|---|---|---|']
    for group, ids in source['groups'].items():
        for rid, count in Counter(ids).items():
            if count > 1:
                r = records[rid]
                lines.append(f"| {group} | {r['es']} | {r['uk']} | {count} |")
    variants = defaultdict(list)
    for r in records.values():
        variants[normalized(r['es'])].append(r)
    lines += ['', '## Різні українські значення або написання для одного es', '',
              '| es | Збережені uk | Додані en |', '|---|---|---|']
    for rows in variants.values():
        if len(rows) > 1:
            lines.append('| '+rows[0]['es']+' | '+'; '.join(r['uk'] for r in rows)+' | '+'; '.join(r['en'] for r in rows)+' |')
    lines += ['', '## Неоднозначності для окремого редакторського погодження', '',
        '- `mañana`: tomorrow / morning; `poder`: ability / authority; `copa`: glass / trophy;',
        '  `clima`: weather / climate; `papel`: role. Сенси лишаються окремими записами.',
        '- `hocico → ніс`: іспанською це snout/muzzle тварини, не звичайний людський ніс.',
        '- `atte → уважно`: це скорочення Atte. (atentamente), у листах «yours sincerely».',
        '- `attractivo`: імовірна описка в atractivo; es збережено, en — attractive.',
        '- `victimas`: імовірно бракує наголосу víctimas; оригінал збережено.',
        '- `sirena → повітряна тривога`: базове значення siren, також mermaid; air-raid alarm потребує контексту.',
        '- `frente → попереду`, `tarde → вечір`, `cura → одужання`, `navegar → мандрувати`,',
        '  `criado → вихований`, `abundante → щедрий`, `cabal → точний`, `cociente → коефіцієнт`,',
        '  `persistir → наполягати`, `superar → перемагати`, `prevenir → попереджувати`: англійська',
        '  передає іспанський сенс; українські неточності збережено для погодження.',
        '- Адаптовано англійську граматичну форму: fácil/difícil — easy/difficult,',
        '  rápido/lento — fast/slow; старі uk іноді є прислівниками.',
        '- Апострофи в uk мають різні символи (`м’ясо`, `мʼясо`); вони збережені.',
        '', '## Квіз', '',
        'Питання мають стабільні ID; правильна відповідь перевіряється за ID та мовою.',
        'Для кожної мови генеруються чотири непорожні різні варіанти. Інші збережені',
        'значення того самого іспанського слова не використовуються як хибні відповіді.',
        'Варіанти обираються з консервативного банку різних значень уже наявних слів того самого рівня.',
        'Нові A1-питання та неоднозначні початкові A1-записи мають іспанський контекст.',
        'Неоднозначності активного A2 уточнено метаданими й контекстом (A2_EXPANSION.md).',
        'Перелік вище також описує архівні оригінали та початкові проблеми B1/base.',
        '', 'Англійські переклади додано вручну. Незалежна лінгвістична експертиза не проводилася.', '']
    return '\n'.join(lines)


def expansion_report(source):
    info = source['a1_expansion']
    records = {r['id']: r for r in source['records']}
    active = group_records(source, 'A1')
    active_ids = {r['id'] for r in active}
    added_ids = {rid for b in info['batches'] for rid in b['ids']}
    reused_ids = {r['id'] for r in info['reused_existing']}
    labels = {'people':'Знайомство, родина, люди', 'home':'Дім і побут',
              'food':'Їжа, кафе, покупки', 'time':'Числа, час, дати',
              'travel':'Місто, транспорт, подорожі', 'work':'Робота й навчання',
              'health':'Тіло, самопочуття', 'weather_leisure':'Погода, одяг, дозвілля',
              'communication':'Почуття та просте спілкування'}
    lines = ['# Розширення A1', '',
        'Робоча ціль проєкту — щонайменше 600 одиниць, а не норматив CEFR.', '',
        '## Підрахунок і очищення', '',
        f"- Початково: {info['before_entries']} входжень, {info['before_unique_ids']} різних ID.",
        '- Три точні повтори: agua, ayer, mañana. Родові форми hermano/hermana та hijo/hija',
        '  рахуються як одна одиниця в кожній парі; активними лишено hermano та hijo.',
        f"- Після очищення: {info['cleaned_units']} одиниць. Початкові записи лишаються у джерелі.",
        '- Підготовлено 450 кандидатів у порціях 110 / 110 / 110 / 120; три варіанти',
        '  аналогічних конструкцій виключено, а не використано для досягнення кількості.',
        f"- Додано до A1: {len(added_ids & active_ids)} активних одиниць, з них {len(reused_ids)}",
        '  уже були в загальному каталозі. Для них повторно використано стабільні ID;',
        '  артикль, контекст та уточнення перекладів задаються лише в метаданих A1.',
        f"- Нових активних одиниць у загальному каталозі: {len((added_ids & active_ids) - reused_ids)}.",
        f"- Підсумок A1: **{len(active)} унікальні активні одиниці**. Артиклі й відмінювання",
        '  в прикладах не створюють додаткових одиниць.', '',
        '## Тематичне покриття', '',
        '| Тема | Після очищення | Додано до A1 | Із них уже були в каталозі | Нові в каталозі | Разом A1 |',
        '|---|---:|---:|---:|---:|---:|']
    for topic, label in labels.items():
        old = sum(r['topic']==topic and r['id'] not in added_ids for r in active)
        new = sum(r['topic']==topic and r['id'] in added_ids for r in active)
        reuse = sum(r['topic']==topic and r['id'] in reused_ids for r in active)
        lines.append(f'| {label} | {old} | {new} | {reuse} | {new-reuse} | {old+new} |')
    lines += ['', 'Комунікаційна тема включає також початкові займенники, сполучники та прислівники.',
              '', '## Перевірені порції', '', '| Порція | Кандидати | Активні після редакторського очищення |', '|---|---:|---:|']
    for b in info['batches']:
        lines.append(f"| {b['number']} | {b['count']} | {sum(rid in active_ids for rid in b['ids'])} |")
    lines += ['', '## Виключені нові конструкції', '']
    for r in info['excluded_new_candidates']:
        lines.append('- `'+r['es']+'`: повтор запиту допомоги або конструкції «де розташоване місце»; збережено в архіві, не видається ботом/квізом.')
    lines += ['', '## Перетини з іншими списками', '',
              '| Список | Початковий A1: точні ID | Початковий A1: нормалізовані леми | Поточний A1: нормалізовані леми |',
              '|---|---:|---:|---:|']
    baseline = json.loads((ROOT / 'tests' / 'a1_baseline.json').read_text())
    before_ids = baseline['a1_before']
    before_lemmas = {unit_key(records[rid]['es']) for rid in before_ids}
    after_lemmas = {unit_key(r['lemma']) for r in active}
    for group in ('base','A2','B1'):
        other_ids = set(baseline['unchanged_groups'][group] if group == 'A2' and 'a2_expansion' in source else source['groups'][group])
        other_lemmas = {unit_key(records[rid]['es']) for rid in other_ids}
        lines.append(f'| {group} | {len(set(before_ids)&other_ids)} | {len(before_lemmas&other_lemmas)} | {len(after_lemmas&other_lemmas)} |')
    lines += ['', 'Перетин між рівнями допустим: це повторне використання лексики, не додаткові одиниці',
        'всередині A1. Лема нормалізує регістр, пунктуацію й артикль; відомі родові пари',
        'об’єднано. Іспанські наголоси та ñ не видаляються, бо вони можуть змінювати значення.', '',
        '## Мовна перевірка', '',
        '- Переглянуто es/uk/en, короткі природні приклади та їх переклади для кожної порції.',
        '- Усі 622 A1-записи, включно з 175 початковими, мають контекст трьома мовами.',
        '- Нові іменники подано з артиклем, дієслова — в інфінітиві. Імена країн і назви',
        '  місяців зберігають природне написання без механічного додавання артикля.',
        '- У A1 уточнено tierra → soil/ґрунт, pollo → chicken/курятина, baño → bathroom/ванна кімната,',
        '  piso → flat, tiempo → time, mañana → tomorrow, poder → to be able to.',
        '- Окремі нові сенси: dirección → address (не direction), subir → to go up (не upload),',
        '  aburrido зі estar → bored (не boring зі ser). Контекст показується у питанні.',
        '- Запит лікаря виправлено на ¿Dónde le duele?; llover → дощити, nevar → сніжити.',
        '- Регіон ES позначає типове вживання в Іспанії, не виключність: coche, salón, grifo,',
        '  aparcamiento, patata, billete, ordenador, móvil, jersey, enfadado та початковий piso.',
        '- У квізі використано консервативний банк різних значень наявних іменників A1.',
        '  Для кожного набору перевірено один правильний і три неправильні варіанти uk/en;',
        '  інші переклади тієї самої леми й тієї самої одиниці виключено. Приклади',
        '  перекладаються після відповіді, не підказуючи переклад до вибору.',
        '- Нові слова не є рідкісними словами чи складними ідіомами; навчальний рівень',
        '  визначено для цього проєкту. Приклади можуть містити знайомі форми з інших уроків.', '',
        '## Невирішені питання', '',
        'Сумнівних нових записів в активному A1 після цього перегляду не залишено. Незалежної',
        'експертизи викладачем не проводилося. Початкові проблеми A2/B1 та базового списку',
        '(hocico, atte, attractivo тощо) з DATA_AUDIT.md не входять у це розширення й лишаються',
        'для окремого редакторського погодження. Рівні інших списків не переглядалися.', '',
        '## Схема і відтворення', '',
        '`data/learning.json` — єдине редаговане джерело. Поля нових одиниць: id, es, uk, en,',
        'level, topic, type (word/expression), lemma, part_of_speech, example {es,uk,en}, region.',
        '`group_metadata.A1` сумісно доповнює/уточнює лише представлення A1 для старих ID.',
        'Початкові записи, base/A2/B1 та вірші не переписані. Архівні кандидати не включені в групу A1.', '',
        '```sh', 'python tools/build_learning.py --bot-root ../telegram_bot',
        'python tools/build_learning.py --bot-root ../telegram_bot --check', '```', '',
        'Згенеровані дані включають бот-копію джерела, SOURCE.json і JSON квізу. A2/B1 залишаються',
        'побайтно такими, як до цього завдання. Publication та live-перевірки не виконувалися.', '']
    return '\n'.join(lines)


def a2_expansion_report(source):
    info = source['a2_expansion']
    active = group_records(source, 'A2')
    active_ids = {r['id'] for r in active}
    batch_ids = {rid for b in info['batches'] for rid in b['ids']}
    baseline = json.loads((ROOT/'tests/a2_baseline.json').read_text())
    records = {r['id']: r for r in source['records']}
    a1_keys = {a2_unit_key(r['es']) for r in group_records(source, 'A1')}
    before_keys = {a2_unit_key(records[rid]['es']) for rid in baseline['a2_before']}
    added = [r for r in active if r['id'] in batch_ids]
    overlap = [r for r in active if a2_unit_key(r['es']) in a1_keys]
    reused = {r['id'] for r in info['reused_existing']}
    labels = dict(daily='Щоденні справи, звички та плани', housing='Житло, оренда та побут',
        work_study='Робота, навчання та професії', travel='Подорожі й транспорт',
        shopping='Покупки, оплата та повернення', cooking='Кафе та приготування їжі',
        health='Самопочуття, лікар та аптека', relationships='Стосунки й домовленості',
        services='Послуги, телефон та інтернет', past_events='Минулі події та життєві ситуації')
    lines = ['# Розширення A2', '', 'Ціль ≥1000 — робоча ціль проєкту, не норматив CEFR.', '',
        '## Кількість та очищення', '',
        f"- До очищення: {info['before_entries']} входжень, {info['before_ids']} ID, {len(before_keys)} нормалізовані одиниці.",
        f"- Після початкового очищення: {info['cleaned_units']} одиниці.",
        '- Точні повтори museo/sangre/victoria та родові пари hermano/hermana, hijo/hija, abuelo/abuela об’єднано.',
        '- hocico → ніс виключено з активного A2: це морда тварини, не людський ніс. Оригінал збережено.',
        f"- Додано до активного A2: {len(added)} одиниць; {len(reused)} використовують наявні ID каталогу.",
        f"- Нових активних записів каталогу: {len(added)-len(reused)}.",
        f"- Підсумок: **{len(active)} унікальні одиниці**; однакові леми з різними сенсами рахуються лише з контекстом.", '',
        '## Додані одиниці за темами', '', '| Тема | Додано |', '|---|---:|']
    for topic, label in labels.items():
        lines.append(f"| {label} | {sum(r['topic']==topic for r in added)} |")
    lines += ['', '## Порції та відхилені кандидати', '', '| Порція | Кандидатів | Прийнято | Активних після перегляду |', '|---|---:|---:|---:|']
    for b in info['batches']:
        lines.append(f"| {b['number']} | {b['candidate_count']} | {b['count']} | {sum(rid in active_ids for rid in b['ids'])} |")
    lines.append('')
    for r in info['rejected_candidates']+info['excluded_new_candidates']:
        lines.append('- `'+r['es']+'`: '+r['reason'])
    lines += ['', '## Перетини з A1', '',
        f"- До змін: {len(before_keys & a1_keys)} спільних нормалізованих лем із поточним A1.",
        f"- Після: {len({a2_unit_key(r['es']) for r in overlap})} спільних лем; {len(overlap)} одиниць A2.",
        '- Стару базову лексику у A2 збережено, але повторно не додано для досягнення цілі.',
        '- Нові перетини допускаються лише для окремого значення з іспанським контекстом:', '']
    for r in added:
        if a2_unit_key(r['es']) in a1_keys:
            lines.append(f"  - `{r['es']}` → {r['en']} (`{r.get('sense')}`); {r['example']['es']}")
    lines += ['', '## Мовний перегляд', '',
        '- Переглянуто всі нові es/uk/en, приклади трьома мовами та варіанти відповідей.',
        '- Артиклі, інфінітиви, зворотні форми та потрібні прийменники збережено. Приклади не рахуються як нові одиниці.',
        '- Уточнено початкові tarde, clima, baño, cura, navegar, sirena, poder, aburrido, dirección та інші неоднозначності.',
        '- Іспанські оригінали каталогу збережено; виправлення та артиклі старих A2 задаються через group_metadata.A2.',
        '- víctima(s): наголос виправлено лише у представленні A2, ID збережено.',
        '- Розділено cuenta (restaurant bill/bank account), receta (medical prescription/cooking recipe), picar (snack/chop), sobre (about/envelope).',
        '- Для однакових значень costumbre/plazo/devolver/cobrar/cobertura/solicitar повторно використано початкові ID.',
        '- Позначено ES для характерних іспанських термінів; computadora має примітку Latin America. Це поширеність, не виключність.',
        '- Квіз використовує 1 правильний та 3 хибні варіанти з консервативного банку різних іменників цього рівня.',
        '- Усі переклади тієї самої леми вилучено з хибних варіантів; dinero не є дистрактором до cash/balance.',
        '- До відповіді показується тільки іспанський приклад, його переклад — після вибору.', '',
        '## Сумісність і перевірки', '',
        '- A1/B1 JSON, їх групи, метадані A1, базовий список і вірші перевіряються за знімком до A2.',
        '- Початкові 1638 записів каталогу збережено без змін, що перевірено канонічним JSON-хешем.',
        '- Бот і квіз одержують одні записи зі спільного data/learning.json; ID збережено при повторному використанні.',
        '- Автоматичні Python/Node тести перевіряють видачу, оцінювання, uk/en, рівні, Premium та платіжні сценарії із підмінами.',
        '- Прогін цього завдання (2026-10-05): 94 Python та 25 Node тестів пройшли; пропусків і збоїв немає.',
        '- build_learning.py --check підтвердив відповідність усіх 8 згенерованих артефактів; git diff --check без помилок.',
        '- Telegram, Google Sheets та платежі наживо не перевірялись. Зміни не опубліковано; розсилок не виконано.', '',
        '## Змінені файли', '',
        'У spanish_quiz:', '',
        '- data/learning.json — спільне редаговане джерело, A2 та метадані.',
        '- data/A2.json — згенеровані питання uk/en.',
        '- tools/build_learning.py — дистрактори й звіти.',
        '- tools/learning_schema.py — перевірка A2, форм і сенсів.',
        '- index.html — регіональна примітка потрібною мовою.',
        '- tests/quiz.test.cjs — проходження A2, контекст та регіональні примітки.',
        '- tests/a2_baseline.json — знімок до змін для захисту інших даних.',
        '- DATA_AUDIT.md — оновлений аудит.',
        '- A2_EXPANSION.md — цей звіт.', '',
        'У telegram_bot:', '',
        '- data/learning.json — згенерована копія спільного джерела.',
        '- data/SOURCE.json — походження й контрольний хеш.',
        '- serhii_spanish_bot.py — артиклі A2, архівні ID та регіональні примітки.',
        '- tests/test_a2_expansion.py — A2 та перевірки збереження інших даних.',
        '- tests/test_a1_expansion.py — старий тест незмінності A2 замінено перевірками нового знімка.',
        '- tests/test_localization.py — враховує навмисне розширення A2, перевіряє збереження оригіналів.', '',
        '## Невирішені мовні питання', '',
        'Сумнівних нових одиниць після цього перегляду не залишено. Незалежна експертиза викладачем не проводилася.',
        'Складність окремих початкових слів A2 (наприклад transfusión, hemorragia, heroísmo) вища за типові побутові теми;',
        'їх рівні у цьому завданні не змінювалися. Проблеми початкових base/B1 (atte, attractivo тощо) лишаються поза обсягом.',
        'A1_EXPANSION.md є історичним звітом попередньої роботи, його перетини A2 наведено для бази до цього розширення.', '',
        '## Налаштування та ручна перевірка після майбутньої публікації', '',
        'Нова конфігурація Render/Google Sheets, секрети чи міграція Premium не потрібні.',
        'Розгортати бот і WebApp узгоджено; для перевірки відкрити новий квіз (очистити старий кеш за потреби).',
        'Старий текстовий формат результатів та ID виключених початкових A2-записів підтримано для кешованих питань.',
        'Точний commit розгорнутої версії буде відомий лише після окремо погодженої публікації.', '',
        '| Дія | Очікувано | Зміна даних |', '|---|---|---|',
        '| /language → Українська / English | Меню відповідною мовою | Зберігає вашу мову в Users/локальному сховищі |',
        '| Premium → A2 → 📗 Слова цього рівня; відповісти | Слово, правильність, приклад і переклад потрібною мовою | Тимчасовий стан вашого запитання; таблиці не змінює |',
        '| Обрати A2; /quiz → відкрити; пройти й завершити, повторити uk/en | Іспанський контекст до відповіді, переклад після; правильний результат у боті | Надсилає результат у ваш чат; таблиці не змінює |',
        '| Перемкнути A1/B1 | Попередні матеріали й поведінка | Тимчасово змінює ваш вибраний рівень |',
        'Оплати, масові дії, зміни чужих доступів у звичайний ручний тест не включати.', '',
        '```sh', 'python tools/build_learning.py --bot-root ../telegram_bot',
        'python tools/build_learning.py --bot-root ../telegram_bot --check', '```', '']
    return '\n'.join(lines)


def b1_expansion_report(source):
    info = source['b1_expansion']
    active = group_records(source, 'B1')
    new_ids = {rid for b in info['batches'] for rid in b['ids']}
    added = [r for r in active if r['id'] in new_ids]
    active_ids = {r['id'] for r in active}
    baseline = json.loads((ROOT/'tests/b1_baseline.json').read_text())
    original = {r['id']: r for r in source['records']}
    before_keys = {b1_unit_key(original[rid]['es']) for rid in baseline['before']}
    labels = {'work':'Робота та професійні ситуації', 'education':'Освіта й розвиток',
              'travel':'Подорожі та скарги', 'housing':'Житло, договори та послуги',
              'health':'Здоров’я та спосіб життя', 'relationships':'Стосунки й домовленості',
              'technology':'Технології, медіа та онлайн', 'society':'Суспільство, культура та довкілля',
              'money':'Гроші та споживчі рішення', 'life':'Досвід, цілі та життєві зміни'}
    lines = ['# Розширення B1', '', 'Щонайменше 1500 одиниць — робоча ціль проєкту, не норматив CEFR.', '',
        '## Кількість', '',
        f"- Початково: {info['before_entries']} входжень, {info['before_ids']} ID, {info['before_lemmas']} нормалізована лема.",
        f"- Після очищення: {info['cleaned_units']} одиниць.",
        '- Прибрано повтори однакових лем/значень, attractivo/atractivo, asunto/asuntos, абревіатуру atte та відмінювану форму continúa.',
        '- Оригінали та ID залишаються в каталозі; виключені записи не видаються як нові питання.',
        '- Обидва початкові ID cifra збережено: digit та numerical figure мають різні значення й окремий контекст.',
        f"- Підготовлено 840 кандидатів: 40 слабших конструкцій замінено самостійними висловами, 4 додатково виключено.",
        f"- Додано до активного B1: {len(added)} одиниць; підсумок **{len(active)}**.",
        '- Усі нові записи — дієслівні словосполучення або самостійні вислови; нових простих іменників немає.',
        '- Приклади, займенникові та відмінювані форми не створюють додаткових одиниць.', '',
        '## Нові одиниці за темами', '', '| Тема | Додано |', '|---|---:|']
    for topic,label in labels.items():lines.append(f"| {label} | {sum(r['topic']==topic for r in added)} |")
    lines += ['', '## Порції', '', '| Порція | Прийнято | Активних після перегляду |', '|---|---:|---:|']
    for b in info['batches']:lines.append(f"| {b['number']} | {b['count']} | {sum(rid in active_ids for rid in b['ids'])} |")
    lines += ['', '40 редакторських замін входять у ті самі порції; кількість у кожній — 100–150.', '', '## Виключені початкові входження', '']
    for row in info['excluded_occurrences']:
        lines.append('- `'+row['es']+'` (`'+row['id']+'`): '+row['reason'])
    lines += ['', '## Перетини з A1/A2', '', '| Рівень | До: спільні леми | Після: спільні леми | Серед нових B1 |', '|---|---:|---:|---:|']
    for group in ('A1','A2'):
        keys={b1_unit_key(r['es']) for r in group_records(source,group)}
        lines.append(f"| {group} | {len(before_keys & keys)} | {len({b1_unit_key(r['es']) for r in active} & keys)} | {sum(b1_unit_key(r['es']) in keys for r in added)} |")
    lines += ['', 'Чотири нові збіги з A2 виникли лише через уточнення прийменників початкових B1 (confiar en, acostumbrarse a тощо).',
        'Нову базову лексику A1/A2 повторно не додано. Самостійні B1-колокації можуть містити вже знайомі слова.', '',
        '## Мовний перегляд і квіз', '',
        '- Переглянуто всі нові es/uk/en та приклади. Короткі речення використовують повторювані граматичні рамки;',
        '  ці рамки не є додатковими одиницями. Є минулий досвід, плани, умови, причини, поради та думки.',
        '- Зворотні інфінітиви в прикладах узгоджено: incorporarme/incorporarnos, prepararme/prepararnos тощо.',
        '- Уточнено початкові copa (trophy), papel (role), carrera (career), compañía (company), seguro (safe),',
        '  guía (guidebook), clima (climate), patrón (pattern), bote (boat), fondo (fund) та інші значення.',
        '- Відновлено прийменники/зворотність: depender de, participar en, renunciar a, carecer de, cerciorarse de тощо.',
        '- Виправлено українські неточності abundante, cabal, cociente, persistir, superar, prevenir у метаданих B1.',
        '- ES позначає характерне іспанське вживання; feriado має Latin America. Примітки не стверджують виключності.',
        '- Поле register: neutral/formal/colloquial; позначки формального й розмовного регістру локалізовані.',
        '- Правильна відповідь та три хибні варіанти формуються з одного джерела. Виключено альтернативні переклади тієї самої леми.',
        '- Для нових конструкцій використано консервативний банк семантично інших іменників; дистрактори однозначні, але навмисно нескладні.',
        '- Переклад прикладу не показується до відповіді. Нові B1 та неоднозначні початкові записи мають іспанський контекст.', '',
        '## Збереження даних та перевірки', '',
        '- A1/A2 JSON перевіряються побайтними хешами; групи та метадані A1/A2, base й вірші — знімком до завдання.',
        '- Початкові 2191 записи каталогу збережено без змін; уточнення існуючих ID задаються через group_metadata.B1.',
        '- Python тести перевіряють видачу й оцінювання слів/квізу uk/en, мову, рівні та Premium із суворими підмінами.',
        '- Node тести перевіряють інтерфейс, контекст, регістр та передачу результатів через підміну Telegram WebApp.',
        '- Прогін цього завдання (2026-10-05): 108 Python та 28 Node тестів пройшли, без пропусків і збоїв.',
        '- build_learning.py --check підтвердив усі 9 згенерованих артефактів; git diff --check без помилок.',
        '- Реальні Telegram/Sheets, платежі й Render не запускалися. Публікації та розсилок не було.', '',
        '## Невирішені мовні питання', '',
        '- Сумнівних нових записів після перегляду не залишено; незалежна перевірка викладачем не проводилася.',
        '- Частина початкового B1 містить книжні/спеціалізовані слова (arqueología, cociente, atroz тощо).',
        '  Їх рівні не змінювалися. Рівень у цьому проєкті не є сертифікацією CEFR.',
        '- Близькі значення різних колокацій допустимі як різні способи вираження думки;',
        '  їх синонімічні переклади не використовуються як хибні варіанти.', '',
        '## Змінені файли', '',
        'У spanish_quiz: data/learning.json, data/B1.json, tools/learning_schema.py, tools/build_learning.py,',
        'index.html, tests/quiz.test.cjs, tests/b1_baseline.json, DATA_AUDIT.md, B1_EXPANSION.md.', '',
        'У telegram_bot: data/learning.json, data/SOURCE.json, serhii_spanish_bot.py, tests/test_b1_expansion.py,',
        'tests/test_a1_expansion.py, tests/test_a2_expansion.py, tests/test_localization.py.', '',
        '## Налаштування та ручні сценарії після погодженого deploy', '',
        'Нові секрети, конфігурація Render/Sheets або міграція Premium не потрібні. Узгоджено оновити бот і WebApp.',
        'A1_EXPANSION.md та A2_EXPANSION.md — історичні звіти попередніх завдань.', '',
        '| Дія | Очікувано | Дані |', '|---|---|---|',
        '| /language → Українська / English | Меню потрібною мовою | Зберігає вашу мову |',
        '| Premium → B1 → 📗 Слова цього рівня; відповісти | Контекст, оцінка, переклад прикладу; примітка регістру за наявності | Тимчасовий стан вашого питання; таблиці не змінює |',
        '| Обрати B1; /quiz; пройти й завершити uk/en | Приклад іспанською до відповіді, переклад після; правильний результат у чаті | Надсилає результат; таблиці та доступи не змінює |',
        '| Перемкнути A1/A2 | Попередній матеріал та поведінка | Лише ваш тимчасовий рівень |',
        'Оплати, зміни чужих доступів та масові дії у звичайний живий тест не включати.', '',
        '```sh', 'python tools/build_learning.py --bot-root ../telegram_bot',
        'python tools/build_learning.py --bot-root ../telegram_bot --check', '```', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bot-root', type=Path, default=ROOT.parent / 'telegram_bot')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    source = json.loads((ROOT / 'data' / 'learning.json').read_text())
    outputs = {path: json.dumps(data, ensure_ascii=False, indent=2)+'\n'
               for path, data in artifacts(source, args.bot_root).items()}
    outputs[ROOT / 'DATA_AUDIT.md'] = report(source)
    if 'a1_expansion' in source:
        outputs[ROOT / 'A1_EXPANSION.md'] = expansion_report(source)
    if 'a2_expansion' in source:
        outputs[ROOT / 'A2_EXPANSION.md'] = a2_expansion_report(source)
    if 'b1_expansion' in source:
        outputs[ROOT / 'B1_EXPANSION.md'] = b1_expansion_report(source)
    digest = hashlib.sha256((ROOT / 'data' / 'learning.json').read_bytes()).hexdigest()
    outputs[args.bot_root / 'data' / 'SOURCE.json'] = json.dumps({
        'repository': 'serhiisurgeon-collab/spanish_quiz',
        'path': 'data/learning.json', 'sha256': digest,
        'generated_by': 'spanish_quiz/tools/build_learning.py'}, indent=2)+'\n'
    for path, data in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != data:
                raise SystemExit('Generated file is stale: '+str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
    print(f"{'Checked' if args.check else 'Generated'} {len(outputs)} artifacts; {len(source['records'])} translations")


if __name__ == '__main__':
    main()
