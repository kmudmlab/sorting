"""Build a file-openable assignment page, sharing the instructor-owned drivers."""
from pathlib import Path
import importlib.util
import json
import html

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('engine', root / 'assignment_engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
template = (root / 'assignments.template.html').read_text()
config_file = root / 'submission-api.json'
config = json.loads(config_file.read_text()) if config_file.exists() else {'url': ''}
output = template.replace('__ASSIGNMENTS__', json.dumps(engine.ASSIGNMENTS, ensure_ascii=False))
output = output.replace('__SUBMIT_CONFIG__', json.dumps(config, ensure_ascii=False))
output = output.replace('__ENGINE__', (root / 'assignment_engine.py').read_text())
if config.get('portalUrl'):
    portal = html.escape(config['portalUrl'], quote=True)
    banner = '<aside class="notice"><strong>새 과제 제출은 학교 계정으로 로그인하세요.</strong> <a href="'+portal+'">새 과제 사이트 열기</a><p>이 화면은 이전 코드 확인·연습·Google Form 접수 조회용입니다. 새 제출은 받지 않습니다.</p></aside>'
    legacy = output.replace('<main>', '<main>'+banner, 1)
    legacy = legacy.replace("$('submit').disabled=locked", "$('submit').disabled=true||locked")
    legacy = legacy.replace("$('submit').textContent=app.submitting?", "$('submit').textContent=true?'새 사이트에서 제출하세요':app.submitting?")
    start = legacy.index('async function submit(){')
    end = legacy.index('const RECEIPT_STORAGE=', start)
    legacy = legacy[:start]+"function submit(){notice('학교 계정으로 새 과제 사이트에서 제출하세요.',true);}\n"+legacy[end:]
    (root/'assignments-legacy.html').write_text(legacy)
    output = (root/'portal.template.html').read_text().replace('__PORTAL_URL__', portal)
(root / 'assignments.html').write_text(output)
print('Built assignments.html')
