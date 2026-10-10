#!/usr/bin/python3
"""Explicit fresh-disposable-VM enrollment with the Ubuntu package's nginx.service as the governed unit.

Same admission, one-use grant, identity and exclusivity semantics as
scripts/enroll-local-fixture.py. The difference: no fixture unit is created and
nothing is masked; the request names the packaged unit `nginx.service`
(per-enrollment `unit_name`, which needs a Workbench that reads it; the
licensing candidate's 0.1.0 fixes the unit). Observation is systemd unit state only: HTTP health of nginx is NOT
instrumented by this candidate's target enrollment.
"""
import argparse, hashlib, json, os, pathlib, subprocess, time, uuid, urllib.request
from operational_ecad import live_instrumentation
from operational_ecad.live_instrumentation import canonical, digest, validate, apply, UNIT
from operational_ecad.live_workbench import validate_manifest
from operational_ecad.live_gateway import validate as validate_config
P=pathlib.Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidate',type=P,required=True)
p.add_argument('--admit-disposable-unit-start',action='store_true',required=True)
p.add_argument('--principal',default='test-owner')
p.add_argument('--runtime-identities',type=P,help='lab only: identity manifest replacing the candidate RUNTIME-IDENTITIES.json (rebuilt Workbench)')
a=p.parse_args()
GOVERNED='nginx.service'
if os.geteuid()!=0: p.error('root owner required')
if not hasattr(live_instrumentation,'request_unit'): p.error('installed Workbench fixes the governed unit to '+UNIT+'; governing nginx.service needs a Workbench that reads unit_name')
r=a.candidate.resolve()
# An independently verified candidate directory is a prerequisite, not a grant.
subprocess.run(['sha256sum','--check','--quiet','SHA256SUMS'],cwd=r,check=True)
identities=json.loads((a.runtime_identities or r/'RUNTIME-IDENTITIES.json').read_text())
for f in identities['files']:
 actual=P(f['path'])
 if actual.is_symlink() or not actual.is_file() or hashlib.sha256(actual.read_bytes()).hexdigest()!=f['sha256']:
  p.error('installed candidate identity mismatch: '+str(actual))
owned=P('/var/lib/constellation-live-ecad')
for path in [owned,P('/etc/constellation-live-ecad'),P('/etc/nq/nqd-ops.toml'),P('/var/lib/nq-ops'),P('/etc/systemd/system/nqd-ops.service'),P('/etc/systemd/system/constellation-live-reader.service'),P('/usr/libexec/agent-governor-ng/ag-effectd.deployment.json'),P('/usr/bin/docket-standing-grant-resolver.enrollment.json'),P('/etc/constellation-workbench/live-cohort.json'),P('/etc/constellation-workbench/gateway.json'),P('/etc/systemd/system/'+UNIT),P('/etc/systemd/system/'+GOVERNED)]:
 if os.path.lexists(path): p.error('existing enrollment/fixture requires owner reconciliation: '+str(path))
# The service under governance must be the distribution's nginx, installed and with a valid configuration.
for binary in ('/usr/sbin/nginx','/lib/systemd/system/nginx.service'):
 if subprocess.run(['dpkg-query','--search',binary],capture_output=True).returncode: p.error('nginx from the Ubuntu package is required: '+binary)
if subprocess.run(['/usr/sbin/nginx','-t','-q'],capture_output=True).returncode: p.error('nginx configuration test failed; fix nginx before enrollment')
show=dict(l.split('=',1) for l in subprocess.check_output(['systemctl','show',GOVERNED,'--property=FragmentPath,DropInPaths,UnitFileState,ActiveState'],text=True).splitlines() if '=' in l)
# The measured identity is the packaged fragment; drop-ins would change behaviour outside it.
if show.get('FragmentPath')!='/lib/systemd/system/'+GOVERNED or show.get('DropInPaths') or show.get('UnitFileState')!='enabled' or show.get('ActiveState')!='active':
 p.error('need the packaged nginx.service enabled, active and without drop-ins: '+json.dumps(show,sort_keys=True))
run_id=str(uuid.uuid4()); now=int(time.time()*1000)
components=identities['components']
def profile(id,version):
 return digest(canonical(json.loads(subprocess.check_output(['/usr/bin/nq','--json','profiles','show',id,str(version)]))))
pins={'systemd':profile('nq.systemd_unit',3),'http':profile('nq.http_endpoint',1)}
request={'schema':'operational_ecad.instrumentation_request/v1','run_id':run_id,'role':'target','host_id':'operator-vm','site':'human-local','components':components,'profile_digests':pins,'service_subject':None,'promotions':[],'unit_name':GOVERNED}
admission={'schema':'operational_ecad.instrumentation_apply_admission/v1','run_id':run_id,'role':'target','request_sha256':digest(canonical(request)),'principal':a.principal,'expires_at_unix_ms':now+7200000,'effects':['configure_nq','enroll_nq_helpers','start_live_reader','enroll_exact_systemd_start'],'max_execution_uses':1}
marker={'schema':'constellation.live-cohort-guest-ownership/v1','run_id':run_id,'role':'target'}
validate(request,admission,marker,now)
owned.mkdir(mode=0o700)
def exclusive(path,value,mode=0o600):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
 with os.fdopen(fd,'wb') as out: out.write(value); out.flush(); os.fsync(out.fileno())
exclusive(owned/'OWNERSHIP.json',canonical(marker))
exclusive(owned/'request.json',canonical(request)); exclusive(owned/'admission.json',canonical(admission))
# Exactly one apply. Partial effects preserve the exclusive claim for reconciliation.
public=apply(request,admission)
machine=public['machine_id']
if public['service_subject']['unit_name']!=GOVERNED: p.error('enrollment measured an unexpected unit: '+public['service_subject']['unit_name'])
manifest={'schema':'operational_ecad.live_cohort/v1','cohort_id':run_id,'title':'nginx.service observation and governed recovery','hosts':[{'host_id':'operator-vm','role':'target','machine_id':machine,'components':components}],'capabilities':[{'id':'nginx-required-unit','host_id':'operator-vm','subject_id':'systemd-unit:'+machine+'/'+GOVERNED,'profile':{'id':'nq.systemd_unit','version':3,'digest':pins['systemd']},'required_levels':[1,2,3]}],'diagnostic':{'level':2,'objective':'Inspect current state of nginx.service. Unit active is not service healthy: nginx HTTP is not instrumented. Recovery requires distinct native authority.','budget':{'runtime_ms':900000,'model_calls':0,'cost_microusd':0,'response_bytes':2097152}},'source':{'kind':'exec/v1','argv':['/usr/bin/constellation-live-cohort-read','--config','/etc/constellation-workbench/gateway.json'],'timeout_ms':5000,'max_bytes':2097152}}
gateway={'schema':'operational_ecad.live_gateway/v1','manifest':manifest,'endpoints':{'operator-vm':'http://127.0.0.1:8081/api/read'}}
validate_manifest(manifest); validate_config(gateway)
conf=P('/etc/constellation-workbench'); conf.mkdir(exist_ok=True)
exclusive(conf/'live-cohort.json',canonical(manifest),0o644); exclusive(conf/'gateway.json',canonical(gateway),0o644)
subprocess.run(['systemctl','enable','--now','--quiet','constellation-workbench.service'],check=True)
print(json.dumps({'schema':'constellation.operator-fixture.receipt/v1','run_id':run_id,'expires_at_unix_ms':admission['expires_at_unix_ms'],'max_uses':1,'governed_unit':GOVERNED,'service':'nginx (Ubuntu package unit, unchanged)','entry':'http://127.0.0.1:18861/operator.html','claim':'unit evidence only; nginx HTTP not instrumented; unit active is not service healthy; enrollment does not imply healthy baseline','public_enrollment':str(owned/'public/enrollment.json')}))
