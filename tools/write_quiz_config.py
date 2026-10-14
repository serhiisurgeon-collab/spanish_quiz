"""Public URL only; no Telegram token/keys are sent to the static site."""
import json
import os
from pathlib import Path
from urllib.parse import urlparse
value=os.environ.get('QUIZ_API_URL','').rstrip('/')
url=urlparse(value)
if value and (url.scheme!='https' or not url.netloc or url.username or url.password or url.query or url.fragment):
    raise ValueError('QUIZ_API_URL must be a public HTTPS origin')
(Path(__file__).resolve().parents[1]/'quiz-config.js').write_text('window.QuizConfig = '+json.dumps({'apiBase':value})+';\n')
