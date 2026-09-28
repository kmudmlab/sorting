"""Build a file-openable assignment page, sharing the instructor-owned drivers."""
from pathlib import Path
import importlib.util
import json

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
(root / 'assignments.html').write_text(output)
print('Built assignments.html')
