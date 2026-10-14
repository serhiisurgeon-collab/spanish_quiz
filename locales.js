// Shared keys for all WebApp interface text. Spanish remains the study language.
window.QuizLocales = {
  uk: {
    progressDescription: 'Пройдено {count} із {total} питань',
    secureHint: 'Відповіді зберігаються після перевірки. Натисни «Завершити квіз», коли закінчиш.',
    secureFinish: "Завершити квіз", retry: "Спробувати ще раз", authExpired: "Авторизація застаріла. Закрий квіз і відкрий його заново через бота.", accessDenied: "Немає доступу до квізу або цієї сесії. Відкрий квіз через бота й перевір Premium.", serverError: "Сервер тимчасово недоступний. Спробуй ще раз.", requestError: "Не вдалося узгодити прогрес. Спробуй ще раз або відкрий квіз заново.", timeoutError: "Час очікування вичерпано. Відповідь могла зберегтися; перевіримо її при повторі.", networkError: "Немає зв’язку із сервером. Спробуй ще раз — прогрес перевіримо без повторного обліку.",
    secureCount: 'Прийнято відповідей: {count}. Вони вже збережені у вашому тижневому звіті.', secureResume: 'Попередню відповідь уже збережено. Повторіть той самий вибір або завершіть квіз.', secureSummary: '✅ {correct} · ❌ {incorrect}', secureFinished: 'Квіз завершено. Результати доступні через /myweek у боті.',
    exampleTranslation: 'Переклад прикладу: {example}', context: 'Контекст: {example}', region_ES: 'Вживання: Іспанія',
    title: 'Spanish Quiz by Serhii', heading: 'Мініквіз 🇪🇸', level: 'Рівень {level}',
    prompt: 'Обери правильний переклад слова:',
    hint: 'Обирай відповіді. Натисни «Завершити», щоб надіслати підсумок боту.',
    next: 'Наступне слово 🔁', finish: 'Завершити й надіслати підсумок 🏆',
    loadError: 'Не вдалося завантажити слова для рівня {level}. Спробуйте пізніше.',
    loadWordError: 'Помилка завантаження 😔',
    full: 'Тренування заповнене. Натисни «Завершити», щоб надіслати підсумок.',
    count: 'Відповідей: {count}. Підсумок надійде боту після завершення.',
    correct: '✅ Правильно! «{word}» = «{answer}».',
    wrong: '❌ Невірно. Правильна відповідь: «{answer}».',
    outside: 'Щоб надіслати підсумок, відкрий квіз через кнопку в особистому чаті з ботом.',
    sendError: 'Не вдалося надіслати підсумок. Спробуй ще раз.'
  },
  en: {
    progressDescription: '{count} of {total} questions answered',
    secureHint: 'Answers are saved after grading. Tap “Finish quiz” when you are done.',
    secureFinish: "Finish quiz", retry: "Try again", authExpired: "Authorization expired. Close the quiz and reopen it through the bot.", accessDenied: "You do not have access to this quiz or session. Open it through the bot and check Premium.", serverError: "The server is temporarily unavailable. Please try again.", requestError: "Progress could not be reconciled. Try again or reopen the quiz.", timeoutError: "The request timed out. Your answer may be saved; we will check it when you retry.", networkError: "Could not connect to the server. Try again — progress will be checked without duplicate counting.",
    secureCount: 'Answers accepted: {count}. They are already saved in your weekly report.', secureResume: 'Your previous answer is saved. Repeat the same choice or finish the quiz.', secureSummary: '✅ {correct} · ❌ {incorrect}', secureFinished: 'Quiz completed. Your results are available through /myweek in the bot.',
    exampleTranslation: 'Example translation: {example}', context: 'Context: {example}', region_ES: 'Usage: Spain',
    title: 'Spanish Quiz by Serhii', heading: 'Mini-quiz 🇪🇸', level: 'Level {level}',
    prompt: 'Choose the correct translation:',
    hint: 'Choose your answers. Tap “Finish” to send the result to the bot.',
    next: 'Next word 🔁', finish: 'Finish and send result 🏆',
    loadError: 'Could not load words for level {level}. Please try again later.',
    loadWordError: 'Could not load words 😔',
    full: 'The session is full. Tap “Finish” to send your result.',
    count: 'Answers: {count}. Your result will be sent when you finish.',
    correct: '✅ Correct! “{word}” = “{answer}”.',
    wrong: '❌ Incorrect. Correct answer: “{answer}”.',
    outside: 'To send your result, open the quiz using the button in your private chat with the bot.',
    sendError: 'Could not send your result. Please try again.'
  }
};
