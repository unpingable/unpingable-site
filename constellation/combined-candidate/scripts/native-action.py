#!/usr/bin/python3
"""One explicit native action; no retry, target selection or authority creation."""
import argparse, hashlib, json, pathlib, urllib.request, urllib.error
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=['prepare','init','record-proposal','require-standing','decide','authorize','dispatch','poll','continue','complete','recover'])
p.add_argument('--assessment'); p.add_argument('--prestate',choices=['inactive','failed'])
a=p.parse_args()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
body={'schema':'operational_ecad.live_action/v1','action':a.action}
if a.action=='prepare':
 if not a.assessment or not a.prestate: p.error('prepare requires explicit assessment and prestate')
 with opener.open('http://127.0.0.1:8081/api/assessment-context',timeout=35) as response: ctx=json.load(response)
 if ctx['judgment']['status']!='current': p.error('current native not-active evidence required')
 build=json.loads(pathlib.Path('/usr/share/constellation-workbench/build.json').read_text())
 body.update(prestate=a.prestate,assessment=a.assessment,worker={'identity':'human-operator','tool':'documented-native-api','source_revision':build['source_commit']},observation_sha256='sha256:'+hashlib.sha256(canonical({'evaluation':ctx.get('evaluation'),'observation_export':ctx.get('observation_export')})).hexdigest())
token=pathlib.Path('/var/lib/constellation-live-ecad/private/operator-token').read_text()
request=urllib.request.Request('http://127.0.0.1:8081/api/actions',data=canonical(body),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
try:
 with opener.open(request,timeout=90) as response: print(response.read().decode())
except urllib.error.HTTPError as error:
 print(error.read().decode()); raise SystemExit(2)
