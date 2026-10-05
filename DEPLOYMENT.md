# Release: UK/EN interface and expanded A1

Publication and deployment of this release are explicitly authorized by the user. Git publication and actual Render deployment are separate steps; a successful push alone does not confirm deployment.

Contents: persisted Ukrainian/English preferences, localized bot/WebApp, shared learning source, 622 active A1 units with examples and translated context. Base/A2/B1 and poems are not expanded. Premium policy and prices remain unchanged.

No new secrets or dependencies are required. Retain the existing Render TOKEN, GOOGLE_SHEETS_KEY, persistent disk and BOT_STATE_PATH. Users.language is appended automatically by name when a language preference is saved. SQLite adds only the languages table.

Required order: deploy the bot first and verify its commit and Live status, then deploy the quiz. The new bot accepts legacy Ukrainian quiz messages; the old bot does not support the new ID/lang payload. Do not run a second copy of the main Telegram bot.

Previous published versions:
- bot: befb4bc05b13125c6f296c238a4bd4eb6fbe31eb
- quiz: 3ee00c39ea439ab07af6c18f8541a93372500a08

These are the preceding published recovery releases, reported tested by the user in the conversation. Confirm Render's actual deployed commit in its dashboard before using them as rollback targets. Do not roll the bot back to the older master commit 3d6ef77: its old startup logic can reset lifetime Premium.

Rollback: return the quiz to the previous verified deployment first, then the bot to the preceding recovery release above. Retain the disk, SQLite and Users.language; the older recovery code ignores the new preference fields. Do not restore/delete production data or alter access rights as part of rollback.

Validation before publication: 79 Python tests, 22 Node tests, seven generated artifacts and whitespace checks passed. Telegram/Sheets and payments were mocked; no real integration, billing or user messaging was performed by these checks. Detailed manual scenarios: telegram_bot/A1_CHECKS.md and LOCALIZATION.md.

After deployment, test /language, A1 words and /quiz in both languages from an existing non-admin account, plus /my_status and unchanged A2/B1. Language selection writes only the user's preference; word/quiz practice uses temporary state. Keep payments, access changes and reminder delivery out of normal live testing.
