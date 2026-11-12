"""Inject data.json into template.html -> ../index.html (paths relative to this folder)."""
import json, re, os
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(H, 'data.json')))
t = open(os.path.join(H, 'template.html')).read()
blob = "const DATA = " + json.dumps(d, separators=(',', ':')) + ";"
out = re.sub(r"/\*DATA_START\*/.*?/\*DATA_END\*/", lambda m: "/*DATA_START*/" + blob + "/*DATA_END*/", t, flags=re.S)
open(os.path.join(H, '..', 'index.html'), 'w').write(out); print(len(out))
