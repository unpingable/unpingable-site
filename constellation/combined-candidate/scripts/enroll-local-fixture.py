#!/usr/bin/python3
"""Explicit fresh-disposable-VM enrollment for the prepared operator exercise."""
import argparse, hashlib, json, os, pathlib, subprocess, time, uuid
from operational_ecad.live_instrumentation import canonical, digest, validate, apply
from operational_ecad.live_workbench import validate_manifest
from operational_ecad.live_gateway import validate as validate_config
P=pathlib.Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--candidate',type=P,required=True)
p.add_argument('--admit-disposable-unit-start',action='store_true',required=True)
p.add_argument('--principal',default='test-owner')
a=p.parse_args()
if os.geteuid()!=0: p.error('root owner required')
r=a.candidate.resolve()
# An independently verified candidate directory is a prerequisite, not a grant.
subprocess.run(['sha256sum','--check','SHA256SUMS'],cwd=r,check=True)
identities=json.loads((r/'RUNTIME-IDENTITIES.json').read_text())
for f in identities['files']:
 actual=P(f['path'])
 if actual.is_symlink() or not actual.is_file() or hashlib.sha256(actual.read_bytes()).hexdigest()!=f['sha256']:
  p.error('installed candidate identity mismatch: '+str(actual))
owned=P('/var/lib/constellation-live-ecad')
for path in [owned,P('/etc/constellation-live-ecad'),P('/etc/nq/nqd-ops.toml'),P('/var/lib/nq-ops'),P('/etc/systemd/system/nqd-ops.service'),P('/etc/systemd/system/constellation-live-reader.service'),P('/usr/libexec/agent-governor-ng/ag-effectd.deployment.json'),P('/usr/bin/docket-standing-grant-resolver.enrollment.json'),P('/etc/constellation-workbench/live-cohort.json'),P('/etc/constellation-workbench/gateway.json'),P('/etc/systemd/system/constellation-beta-http-fixture.service')]:
 if os.path.lexists(path): p.error('existing enrollment/fixture requires owner reconciliation: '+str(path))
run_id=str(uuid.uuid4()); now=int(time.time()*1000)
components=identities['components']
def profile(id,version):
 return digest(canonical(json.loads(subprocess.check_output(['/usr/bin/nq','--json','profiles','show',id,str(version)]))))
pins={'systemd':profile('nq.systemd_unit',3),'http':profile('nq.http_endpoint',1)}
request={'schema':'operational_ecad.instrumentation_request/v1','run_id':run_id,'role':'target','host_id':'operator-vm','site':'human-local','components':components,'profile_digests':pins,'service_subject':None,'promotions':[]}
admission={'schema':'operational_ecad.instrumentation_apply_admission/v1','run_id':run_id,'role':'target','request_sha256':digest(canonical(request)),'principal':a.principal,'expires_at_unix_ms':now+7200000,'effects':['configure_nq','enroll_nq_helpers','start_live_reader','enroll_exact_systemd_start'],'max_execution_uses':1}
marker={'schema':'constellation.live-cohort-guest-ownership/v1','run_id':run_id,'role':'target'}
validate(request,admission,marker,now)
owned.mkdir(mode=0o700)
def exclusive(path,value,mode=0o600):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
 with os.fdopen(fd,'wb') as out: out.write(value); out.flush(); os.fsync(out.fileno())
exclusive(owned/'OWNERSHIP.json',canonical(marker))
exclusive(owned/'request.json',canonical(request)); exclusive(owned/'admission.json',canonical(admission))
unit=P('/etc/systemd/system/constellation-beta-http-fixture.service')
exclusive(unit,b'[Unit]\nDescription=Disposable local observation and recovery fixture\n[Service]\nType=simple\nExecStart=/usr/bin/sleep infinity\n[Install]\nWantedBy=multi-user.target\n',0o644)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit.name],check=True)
# Exactly one apply. Partial effects preserve the exclusive claim for reconciliation.
public=apply(request,admission)
machine=public['machine_id']
manifest={'schema':'operational_ecad.live_cohort/v1','cohort_id':run_id,'title':'Local unit observation and governed recovery','hosts':[{'host_id':'operator-vm','role':'target','machine_id':machine,'components':components}],'capabilities':[{'id':'local-required-unit','host_id':'operator-vm','subject_id':'systemd-unit:'+machine+'/'+unit.name,'profile':{'id':'nq.systemd_unit','version':3,'digest':pins['systemd']},'required_levels':[1,2,3]}],'diagnostic':{'level':2,'objective':'Inspect current unit state. HTTP is not instrumented. Recovery requires distinct native authority.','budget':{'runtime_ms':900000,'model_calls':0,'cost_microusd':0,'response_bytes':2097152}},'source':{'kind':'exec/v1','argv':['/usr/bin/constellation-live-cohort-read','--config','/etc/constellation-workbench/gateway.json'],'timeout_ms':5000,'max_bytes':2097152}}
gateway={'schema':'operational_ecad.live_gateway/v1','manifest':manifest,'endpoints':{'operator-vm':'http://127.0.0.1:8081/api/read'}}
validate_manifest(manifest); validate_config(gateway)
conf=P('/etc/constellation-workbench'); conf.mkdir(exist_ok=True)
exclusive(conf/'live-cohort.json',canonical(manifest),0o644); exclusive(conf/'gateway.json',canonical(gateway),0o644)
subprocess.run(['systemctl','enable','--now','constellation-workbench.service'],check=True)
print(json.dumps({'schema':'constellation.operator-fixture.receipt/v1','run_id':run_id,'expires_at_unix_ms':admission['expires_at_unix_ms'],'max_uses':1,'entry':'http://127.0.0.1:18861/operator.html','claim':'unit evidence only; HTTP not instrumented; enrollment does not imply healthy baseline','public_enrollment':str(owned/'public/enrollment.json')}))
