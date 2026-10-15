# Release: reviewed content and twelve learning directions

Authorized for publication/deployment on 2026-10-15. This document describes the prepared release, not confirmation that Render deployed it. Stage five's comprehensive verification remains pending.

## Included

- Completed editorial migration/review of preserved Spanish vocabulary, poems and captions; canonical aliases prevent duplicate material counts without rewriting historical events.
- Four independent UI languages and twelve learning/translation pairs. New UK/EN/DE original curricula have 20 A1, 20 A2 and 20 B1 records each, with three translations and examples. These are starter sets, not complete CEFR courses.
- Eighteen new original AI-generated poems (two per level/language) and six generic captions. The bot labels their origin; existing user-authored Spanish poems retain their authorship and permission.
- Shared generated bot/quiz runtime, reviewed answer choices, persistent material identities and narrow-screen wrapping for long headwords. Quiz sessions remain 20 questions, with server-side authentication/grading, immutable snapshots and idempotent answers/completion.
- Existing Premium/payment rules, personal reports, reminders, announcement IDs and logs retained. No broadcast is part of deployment.

## Before deployment

Record each service's actual current Live commit in Render. Git master previously pointed to bot e8d4927 and quiz 5423c41; these are not independently verified production commit IDs.

Use the CURRENT spanish-bot-web Shell to make an SQLite backup with sqlite3.Connection.backup and verify PRAGMA integrity_check. Do not copy only a live .sqlite3 file without its WAL. Retain the backup privately on the persistent disk; never commit/download it into public artifacts. Existing INTERIM_RELEASE.md contains a backup command. This release makes no new SQLite schema changes relative to those previous master commits; keep the actual current database and disk.

Keep BOT_STATE_PATH=/var/data/spanish-bot/state.sqlite3, TOKEN and GOOGLE_SHEETS_KEY in protected Render configuration, the current single Web Service instance and suspended old worker. No new variables, Sheets tabs or paid resources are required.

## Deployment order

1. Publish both repositories' release commits to master.
2. Render **spanish-bot-web**: Manual Deploy → Deploy a specific commit → published bot commit. Start command remains python -u serhii_spanish_bot.py; health path /health. Wait for Live and check https://spanish-bot-web.onrender.com/health.
3. Render **spanish_quiz**: Manual Deploy → Deploy a specific commit → published quiz commit. Keep its existing build, including tools/write_quiz_config.py with QUIZ_API_URL=https://spanish-bot-web.onrender.com. Reopen the Mini App to load new static assets.
4. Keep QUIZ_WEBAPP_ORIGIN=https://spanish-quiz-kr88.onrender.com on the bot and Auto Deploy off if continuing manual releases. No local second main-bot process.

The new bot remains compatible with older clients/Spanish session snapshots during the rollout. Deploy bot/API first to activate the new pools before publishing their static quiz projections.

## Rollback

Prefer the recorded previous Live deploys, checking their compatibility first. Previous Git master bot e8d4927 already uses the additive language schema and explicit-column inserts. Its older application-level validators do not handle new pairs/DE or ES targets fully: suspend new-direction use until a compatibility fix rather than promising all newly created sessions work after rollback. Existing session/history rows must remain intact. Previous quiz 5423c41 can be restored with the compatible API, but its legacy static pools differ from this reviewed release.

Do not restore an old database over new activity/payment/access history. Keep current SQLite and persistent disk; a pre-deploy backup is for separately assessed recovery. Do not reactivate the old worker or roll back to pre-migration builds without compatibility work.

## Validation and manual checks

Automated offline validation: 261 Python tests, 219 JavaScript tests, generator --check (31 artifacts), git diff --check. Earlier Chromium checks cover all pairs on mobile with intercepted API traffic. These do not constitute live Telegram/Sheets/Render verification.

After both services are Live, verify their exact commits and use your normal non-admin account:

| Action | Expected | Data effect |
|---|---|---|
| /settings: UI Ukrainian, learning German, translation English | Three independent settings | Saves your preferences |
| New word; answer; poem; Next | Correct original/translation; AI attribution only on new project texts | Saves confirmed personal deliveries |
| Existing Premium: B1 → quiz; answer right/wrong, reload, complete | 20 questions; accepted progress restored; server-confirmed result | Saves your session/answers/completion |
| /myweek | Confirmed deliveries and results grouped by learning language; Free has no Premium results | Read-only learning report |
| Repeat UK/EN originals; then Spanish | Appropriate original pools; existing Spanish poems unchanged | Your ordinary learning activity |
| Picture | Existing photo and appropriate bilingual caption | No word/poem counter increment |

Do not test live payments, broadcasts, access changes or forced reminders as ordinary validation.
