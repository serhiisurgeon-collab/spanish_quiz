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
from learning_schema import group_records, unit_key, validate_source

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
    for level in ('A1', 'A2', 'B1'):
        questions = []
        # Distractors stay within this level's existing vocabulary.
        active = group_records(source, level)
        bank = [r for r in active if (unit_key(r['es']) if level == 'A1' else r['es']) in bank_es]
        for r in active:
            rid = r['id']
            output = dict(r)
            options = {}
            for lang in ('uk', 'en'):
                answer = r[lang]
                meaning_key = unit_key(r['es']) if level == 'A1' else normalized(r['es'])
                valid_meanings = (a1_meanings if level == 'A1' else meanings)[meaning_key][lang]
                candidates = [x[lang] for x in bank
                    if normalized(x[lang]) not in valid_meanings
                    and (unit_key(x['es']) if level == 'A1' else normalized(x['es'])) != meaning_key]
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
        ('Базовий список, A2 та B1 збережено; A1 очищено й розширено (див. A1_EXPANSION.md).'
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
        'Початкові неоднозначності A2/B1 лишаються для окремого погодження.',
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
        other_ids = set(source['groups'][group])
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
