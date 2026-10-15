# Interim multilingual release — 2026-10-15

User authorized publication and will perform Manual Deploy on Render. This document describes the release; it does not confirm a production deployment. Earlier stage documents retain historical local-only checkpoints.

## Included

- Four UI languages (uk/en/es/de), /language and /settings; interface, learning language and translation language are independent.
- Existing Spanish-to-Ukrainian and Spanish-to-English learning remain available. Other pairs explicitly show preparation. Premium rules, prices and announcement IDs are preserved; no broadcast is started.
- Shared materials_v2 catalog with 3031 preserved vocabulary IDs; 2357 assistant-reviewed records, 606 pending active vocabulary, 68 excluded archives; poems/captions still pending. New catalog/DE target content is NOT activated in production runtime. Legacy data/learning.json and existing quiz question pools remain the active learning content.
- Additive persistent language metadata for learning events/sessions/telemetry. Older sessions keep question snapshots, grading and history. Historical unknown delivery target language stays unknown.

## Before deploy

1. Open Shell on the CURRENT spanish-bot-web service, not the suspended worker.
2. Back up the current database using SQLite backup, not a live filesystem copy of just the .sqlite3 file. Retain the backup on the current persistent disk. One possible command:

```sh
python -c 'import sqlite3,datetime,os; p=os.environ["BOT_STATE_PATH"]; t=p+".pre-multilingual-"+datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".bak"; s=sqlite3.connect(p); d=sqlite3.connect(t); s.backup(d); result=d.execute("PRAGMA integrity_check").fetchone()[0]; d.close(); s.close(); assert result=="ok"; print("SQLite backup verified:",t)'
```

3. Keep BOT_STATE_PATH=/var/data/spanish-bot/state.sqlite3, the existing disk, secrets, single instance and suspended old worker. Do not start another polling process. No new environment variables/secrets are required.

## Deploy order

1. Render spanish-bot-web: select the newly published bot commit in master; deploy and verify Live and /health.
2. Render spanish_quiz: select the newly published quiz commit in master; deploy and reopen the Mini App.
3. Keep QUIZ_API_URL=https://spanish-bot-web.onrender.com and QUIZ_WEBAPP_ORIGIN=https://spanish-quiz-kr88.onrender.com. Keep Auto Deploy off if retaining manual releases.

Startup performs atomic/idempotent migration: languages CHECK expands to four codes, creates language_preferences, adds interface_language/learning_language/translation_language columns to learning sessions/deliveries/telemetry. Premium/payments/reminders are retained. No new Sheets columns are added; existing Users.language may now store all four UI codes via named-column synchronization.

## Rollback caution

Previous bot b77556e uses positional INSERTs into learning_sessions/learning_deliveries. After new columns are added, a direct code-only rollback to that bot is NOT compatible with new writes. Keep the current database; do not replace it with an older backup after new activity because that would lose new learning/payment/access history. If a rollback is necessary, deploy a compatibility rollback build that retains the additive schema and explicit-column INSERTs while reverting affected UI/behaviour. Do not reactivate the suspended worker. The pre-deploy backup is a recovery checkpoint, not permission to overwrite newer data. Quiz can revert to d6e3689 while keeping the new API; bot retains legacy request compatibility.

## Manual checks after deploy

Use your own non-admin account. No payments, access grants, announcements or reminder sends are part of this check.

| Action | Expected | Writes |
|---|---|---|
| /language → each of four UI languages | Localized menu and command list | Your language preference, mirrored Users.language |
| /settings → Spanish learning + English translations, German UI | Independent settings; supported material in English | Your preferences |
| /word; answer | Spanish/English teaching content with German prompts | Your learning/usage events |
| /settings → German learning + English target; /word | Preparation message, no mislabeled Spanish content | Your preference/usage; no learning delivery |
| Restore Spanish → English; Premium account /quiz | 20 server questions, localized UI, accepted answers and summary | Your quiz session/answers |
| /myweek | Only your own real activity; current Premium controls quiz section | Usage only; no artificial learning activity |
| Reload active quiz after answer | Accepted choice and confirmed progress restored without duplicates | No extra accepted answer |
| Restart service; revisit settings and /myweek | Preferences/history retained | Normal usage only |

Automatic validation: 217 Python tests, 56 JavaScript tests, deterministic migration and shared generator check (13 artifacts). Tests use substitutes/temporary databases. Live Telegram/Sheets/Render validation is pending the user's Manual Deploy. Linguistic review is by assistant; independent human review and complete stage-three identity/distractor/content integration remain pending.
