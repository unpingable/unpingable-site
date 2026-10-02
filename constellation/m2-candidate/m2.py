#!/usr/bin/python3
"""Fixed source-free M2 deployment/runbook operations; no general scheduler."""
import argparse,base64,datetime,hashlib,json,os,pathlib,shutil,sqlite3,subprocess,sys,time,uuid
HERE=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path('/var/lib/constellation-m2')
CONF=pathlib.Path('/etc/constellation-m2')
EFFECTD='/usr/libexec/agent-governor-ng/ag-effectd'
WORK='ag-effectd.docket-executor-systemd-work/v2'
UNIT='constellation-beta-http-fixture.service'
def j(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def raw(b): return 'sha256:'+hashlib.sha256(b).hexdigest()
def digest(v): return raw(j(v))
def domain(d,b):
 d=d.encode();return raw(b'ag-ng\0digest\0v1\0'+len(d).to_bytes(16,'big')+d+len(b).to_bytes(16,'big')+b)
def seal(v,k): v[k]=digest({a:b for a,b in v.items() if a!=k});return v
def write(path,v,mode=0o644):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(j(v));path.chmod(mode)
def read(path):return json.loads(pathlib.Path(path).read_bytes())
def now(): return datetime.datetime.now(datetime.timezone.utc)
def stamp(t=None):
 t=t or now();t=t.replace(microsecond=(t.microsecond//1000)*1000)
 return t.isoformat(timespec='seconds' if t.microsecond==0 else 'milliseconds').replace('+00:00','Z')
def ms(t):return int(t.timestamp()*1000)
def run(args,name=None,json_result=True,input_bytes=None):
 p=subprocess.run([str(a) for a in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,input=input_bytes)
 if name:
  (ROOT/(name+'.stdout')).write_bytes(p.stdout);(ROOT/(name+'.stderr')).write_bytes(p.stderr)
  write(ROOT/(name+'.command.json'),{'argv':[str(a) for a in args],'exit_code':p.returncode,'at':stamp()})
 if p.returncode: raise RuntimeError(f'{args[0]} refused ({p.returncode}): '+p.stderr.decode(errors='replace')[-2000:])
 return json.loads(p.stdout) if json_result else p.stdout

def toml(v):
 if isinstance(v,str):return json.dumps(v)
 if isinstance(v,bool):return 'true' if v else 'false'
 if isinstance(v,int):return str(v)
 if isinstance(v,list):return '['+','.join(toml(a) for a in v)+']'
 if isinstance(v,dict):return '{'+','.join(json.dumps(k)+'='+toml(a) for k,a in v.items())+'}'
 raise ValueError('unsupported config scalar')
def nqconfig(kind,subject,endpoint=None):
 sid=domain('constellation/operator-beta/service-subject/v1',j(subject));profile='nq.'+kind
 descriptor=read('/usr/share/nq/profiles/'+profile+'.v1.json')
 profile_ref={'id':profile,'version':'1','digest':digest(descriptor)}
 scope={'kind':kind,'value':{'schema':'nq.operator_beta.'+kind+'_scope.v1','subject_identity':sid}}
 if kind=='systemd_unit':
  scope['value'].update(target_machine_identity=subject['target_machine_identity'],unit_name=UNIT,unit_file_sha256=subject['unit_file_sha256'],manager_interface='org.freedesktop.systemd1',properties=['LoadState','ActiveState','SubState','UnitFileState']);vantage={'kind':'target_local','value':{}}
  expected={'expected_load_state':'loaded','expected_active_state':'active','expected_sub_state':'running','expected_unit_file_state':'disabled'};cap='read_systemd_unit'
 else:
  controller='machine:'+pathlib.Path('/etc/machine-id').read_text().strip();scope['value'].update(controller_vantage_identity=controller,endpoint=endpoint,method='GET',redirect_policy='refuse',max_response_bytes=1024);vantage={'kind':'controller_http','value':{'controller_vantage_identity':controller}}
  expected={'expected_status':200,'expected_body_sha256':raw((HERE/'fixture/healthz').read_bytes())};cap='read_http_endpoint'
 scope_id={'id':'nq.scope.'+kind,'version':'1','digest':digest({'schema':'nq.diagnostic_scope.v1','subject':sid,'scope':scope,'profile':profile_ref})}
 policy={'schema':'nq.operator_beta.'+kind+'_threshold_policy.v1','fixture_run_id':subject['fixture_run_id'],'service_subject':subject,'subject_identity':sid,'request_scope':scope_id,**expected}
 watcher={'instance_id':kind,'carrier':'stdio','subject':sid,'capability_ceiling':[cap],'checkpoint_policy':'disabled','command':{'executable':'/usr/lib/nq/helpers/nq-operator-beta-helper','args':[],'env':{},'execution_account':'nq-helper','working_directory':'/usr/lib/nq/helpers'},'profile':{'id':profile,'version':1},'threshold_policy':{'id':profile+'.postcondition.threshold_policy','version':subject['fixture_run_id'],'digest':digest(policy),'value':policy},'scope':scope,'vantage':vantage,'schedule':{'interval_seconds':300,'jitter_seconds':0,'deadline_ms':30000,'retry_backoff_seconds':10,'max_retry_backoff_seconds':300},'resources':{'max_response_bytes':1048576,'max_stderr_bytes':65536,'max_observations':1,'max_address_space_bytes':536870912,'max_cpu_seconds':60,'max_processes':32,'max_open_files':128,'max_file_bytes':67108864}}
 cfg={'schema':'nq.config.v1','database_path':str(ROOT/'nq.db'),'socket_path':'/run/constellation-m2/nqd.sock','admissions_dir':str(ROOT/'admissions'),'helper_runtime_dir':'/run/constellation-m2/helpers','watchers':[watcher]}
 path=CONF/'nq.toml';path.write_text('\n'.join(k+'='+toml(v) for k,v in cfg.items())+'\n')
 run(['nq','--config',path,'config','check'],json_result=False)
 run(['nq','--config',path,'init'],name='nq-init',json_result=False)
 run(['nq','--config',path,'watcher','admit',kind],name='nq-admission',json_result=False)
 return sid

def collect(kind,label):
 op=['execute',kind] if label=='before' or label=='controller-after' else ['acquire-next-local',kind,'--acquisition-id','m2-'+read(ROOT/'subject.json')['fixture_run_id']+'-'+label]
 out=run(['nq','--config',CONF/'nq.toml','--json','diagnostics']+op,label)
 # Exact artifact identity is returned by the product, never a deployment-invented diagnostic.
 def find(v):
  if isinstance(v,dict):
   if isinstance(v.get('artifact_id'),str):return v['artifact_id']
   for a in v.values():
    got=find(a)
    if got:return got
  return None
 aid=find(out)
 if not aid:raise RuntimeError('NQ did not return an exact artifact identity: '+str(out))
 b=run(['nq','--config',CONF/'nq.toml','diagnostics','export',aid],label+'-export',False);a=json.loads(b);write(ROOT/(label+'.json'),a)
 run(['nq','--config',CONF/'nq.toml','--json','diagnostics','qualify',aid],label+'-admission')
 return a

def prepare_target(run_id):
 if (ROOT/'identity.json').exists():raise RuntimeError('already prepared; inspect existing state instead of reinitializing')
 ROOT.mkdir(mode=0o755,parents=True,exist_ok=True);CONF.mkdir(mode=0o755,exist_ok=True)
 pathlib.Path('/run/constellation-m2/helpers').mkdir(mode=0o711,parents=True,exist_ok=True)
 install=pathlib.Path('/usr/share/constellation-m2');install.mkdir(exist_ok=True)
 shutil.copytree(HERE/'fixture',install/'fixture',dirs_exist_ok=True)
 shutil.copy2(HERE/'fixture'/UNIT,'/etc/systemd/system/'+UNIT)
 run(['systemctl','daemon-reload'],json_result=False)
 state=run(['systemctl','show',UNIT,'--property=LoadState,ActiveState,UnitFileState'],json_result=False).decode()
 if 'ActiveState=inactive' not in state or 'UnitFileState=disabled' not in state:raise RuntimeError('fixture must initially be inactive and disabled: '+state)
 subject={'schema':'constellation.operator_beta.service_subject.v1','campaign_id':'constellation-operator-beta-2026','fixture_run_id':run_id,'target_machine_identity':pathlib.Path('/etc/machine-id').read_text().strip(),'unit_name':UNIT,'unit_file_sha256':raw(pathlib.Path('/etc/systemd/system/'+UNIT).read_bytes())}
 sid=nqconfig('systemd_unit',subject)
 write(ROOT/'subject.json',subject)
 campaign=domain('constellation.m2.campaign/v1',j({'run_id':run_id}));occurrence=str(uuid.uuid4())
 # Generate a fresh VM-local key. The DER conversion supplies ring's PKCS#8 V2 public-key field.
 keys=CONF/'private';keys.mkdir(mode=0o700)
 run(['openssl','genpkey','-algorithm','ED25519','-out',keys/'issuer.pem'],json_result=False)
 private=run(['openssl','pkey','-in',keys/'issuer.pem','-outform','DER'],json_result=False)
 public=run(['openssl','pkey','-in',keys/'issuer.pem','-pubout','-outform','DER'],json_result=False)[-32:]
 if len(private)!=48 or private[:16].hex()!='302e020100300506032b657004220420':raise RuntimeError('unexpected generated PKCS8 format')
 (keys/'issuer.pk8').write_bytes(bytes.fromhex('3051020101300506032b657004220420')+private[-32:]+bytes.fromhex('812100')+public)
 for p in keys.iterdir():p.chmod(0o600)
 write(CONF/'trust.json',{'issuers':[{'issuer_principal':'constellation-m2-release-operator','key_id':'m2-'+run_id,'public_key':base64.urlsafe_b64encode(public).decode().rstrip('=')}]})
 # Only bounded argument binding lives in deployment scope; authority semantics stay in products.
 wrapper=CONF/'observation-resolver';wrapper.write_text('#!/bin/sh\nexec /usr/bin/nightshift-observation-resolver --store /var/lib/constellation-m2/nightshift.sqlite --resolver-id constellation-m2-observation/v1 --default-ttl-ms 60000\n');wrapper.chmod(0o755)
 wrapper=CONF/'ag-standing-resolver';wrapper.write_text('#!/bin/sh\nexec /usr/bin/ag-standing-resolver --mandate-store /etc/constellation-m2/mandates.json --resolver-id constellation-m2-ag-standing/v1 --answer-ttl-ms 60000\n');wrapper.chmod(0o755)
 # NQ owns the observation scope; authority/catalog retain it exactly.
 identity={'run_id':run_id,'campaign':campaign,'occurrence':occurrence,'subject':sid,'issuer_public_key_sha256':raw(public)}
 write(ROOT/'identity.json',identity)
 print(j({'prepared':True,'subject':subject,'identity':identity}).decode())


def support_enrollment(artifact,inputs_id,observation_id,label):
 subject=read(ROOT/'subject.json');cfg=CONF/(label+'-pulse.json');custody=ROOT/('pulse-'+label);custody.mkdir(mode=0o700)
 enrollment={'schema':'pulse.m2_support_config.v1','authority_id':'pulse-m2-local/'+subject['fixture_run_id'],'generation':subject['fixture_run_id'],'local_machine_id':pathlib.Path('/etc/machine-id').read_text().strip(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'family':artifact['profile']['id'].removeprefix('nq.'),'nq_program':'/usr/bin/nq','nq_program_sha256':raw(pathlib.Path('/usr/bin/nq').read_bytes()),'nq_config':str(CONF/'nq.toml'),'nq_config_sha256':raw((CONF/'nq.toml').read_bytes()),'watcher_instance':artifact['profile']['id'].removeprefix('nq.'),'baseline_artifact_id':artifact['artifact_id'],'baseline_bytes_sha256':raw(j(artifact)),'diagnostic_inputs_id':inputs_id,'observation_id':observation_id,'custody_directory':str(custody)}
 write(cfg,enrollment,0o600)
 run(['pulse-m2-support','acquire','--config',cfg],label+'-pulse-acquisition')
 return cfg


def run_target():
 identity=read(ROOT/'identity.json')
 database=ROOT/'campaigns/active.sqlite'
 if database.exists():raise RuntimeError('existing AG occurrence; inspect/recover it; do not restart run-target')
 before=collect('systemd_unit','before')
 if before['outcome']['condition']!='present':raise RuntimeError('fixture precondition must be independently observed as condition present')
 scope=before['subject']['scope']['digest'];subject=identity['subject'];t=now();expiry=ms(t)+60000
 write(CONF/'mandates.json',{'schema':'ag.governed-loop.standing-mandate-store/v1','mandates':[{'subject':subject,'scope':scope,'generation':1,'status':'active','valid_until_unix_ms':expiry}]})
 catalog={'schema':'ag.governed-loop.exact-work-catalog/v2','entries':{WORK:{'work_schema':WORK,'subject':subject,'scope':scope,'observation_basis':{'kind':'nightshift_atoms','requirement':{'required':['condition.condition_present','delivery.not_required'],'forbidden':['condition.unresolved']}}}}}
 write(CONF/'catalog.json',catalog)
 enrollment={'schema':'ag.governed-loop.runtime-profile-enrollment/v1','profile_label':'constellation-m2-'+identity['run_id'],'observation_resolver':str(CONF/'observation-resolver'),'observation_resolver_id':'constellation-m2-observation/v1','standing_resolver':str(CONF/'ag-standing-resolver'),'standing_resolver_id':'constellation-m2-ag-standing/v1','max_standing_ttl_ms':60000,'exact_work_catalog':str(CONF/'catalog.json'),'controlling_review':None,'docket':{'schema':'ag.governed-loop.docket-root-enrollment/v1','docket_program':'/usr/bin/docket','state_directory':str(ROOT/'docket'),'trust_config':str(CONF/'trust.json'),'standing_resolver':'/usr/bin/docket-standing-resolver','executor_adapter':EFFECTD,'issuer_principal':'constellation-m2-release-operator','issuer_key_id':'m2-'+identity['run_id'],'issuer_key':str(CONF/'private/issuer.pk8')},'human_verifier':None}
 write(CONF/'enrollment.json',enrollment)
 sealed=run(['ag-loopctl','seal-runtime-profile','--enrollment',CONF/'enrollment.json','--output',CONF/'runtime-profile.json'],'seal-profile')
 profile=read(CONF/'runtime-profile.json');profile_id=domain('ag.governed-loop.runtime-profile/v1',j(profile))
 write(pathlib.Path(EFFECTD).with_name('ag-effectd.deployment.json'),{'schema':'ag-effectd.deployment/v1','campaign_database':str(database),'expected_runtime_profile':profile_id})
 plan={'schema':'ag-effectd.docket-executor-systemd-plan/v2','attempt_store':str(ROOT/'effect-attempts.sqlite'),'subject':subject,'scope':scope,'effect_index':0,'effect':{'kind':'systemd_unit','target':'constellation-beta-http-fixture','unit':UNIT,'action':'start','expected_active_state':'inactive','expected_unit_file_state':'disabled'},'file_policy':{'max_content_bytes':1024,'trusted_ancestor_uid':0,'trusted_parent_uid':0,'require_private_parent_writes':True},'systemd_machine_identity':read(ROOT/'subject.json')['target_machine_identity'],'authorization':{'expected_runtime_profile':profile_id},'execution_lock_timeout_ms':5000,'job_timeout_ms':30000}
 write(CONF/'plan.json',plan);work=run([EFFECTD,'plan-id',CONF/'plan.json'],json_result=False).decode().strip()
 key={'question_id':before['question']['id'],'subject_id':before['subject']['id'],'profile_id':before['profile']['id'],'vantage_id':before['vantage']['id']}
 binding={field:before[field] for field in ['question','profile','profile_semantic_id','vantage','state_model','evaluator','threshold_policy','projection','subject']}
 binding.update(producer_node_id=before['producer']['node_id'],producer_build=before['producer']['build'],producer_cohort=before['producer']['cohort'],claim_id=before['primary_claim_id'])
 role={'id':'constellation-m2-local-operator','version':'1','digest':domain('constellation.m2.role/v1',b'local-operator')}
 policy=seal({'schema':'nightshift.diagnostic_posture_policy.v2','generation':identity['run_id'],'subject':before['subject'],'role':role,'delivery_required':False,'inventory':[{'binding':binding,'requirement':'mandatory','required_state_bindings':[],'max_age_seconds':60}]},'policy_id')
 inputs=seal({'schema':'nightshift.diagnostic_inputs.v2','inputs':[{'key':key,'status':'delivered','artifact':before}]},'inputs_id')
 schedule={'schedule_id':'m2-one-slot','first_due_at':before['started_at'],'cadence_seconds':300,'jitter_bound_seconds':0,'max_execution_budget_seconds':30,'standing_window_seconds':60}
 slot_basis={'schedule_id':schedule['schedule_id'],'occurrence':0,'key':key,'due_at':before['started_at'],'budget_seconds':30}
 slot={**slot_basis,'slot_id':digest(slot_basis)}
 claim=next(c for c in before['claims'] if c['claim_id']==before['primary_claim_id'])
 artifact={'contract_schema':before['schema'],'profile_semantic_id':before['profile_semantic_id'],'artifact_id':before['artifact_id'],'request_id':before['request_id'],'run_id':before['run_id'],'attempt_interval':before['attempt_interval'],'key':key,'claim_id':claim['claim_id'],'claim':claim,'dependency_acquisitions':[item['acquisition'] for item in before['inputs']['received']]}
 recurrence=seal({'schema':'nightshift.recurrence_evidence.v2','obligations':[{'key':key,'policy':schedule}],'records':[{'key':key,'policy':schedule,'slot':slot,'evidence':{'kind':'completed','attempt':{'attempt_id':before['run_id'],'slot_id':slot['slot_id'],'request_id':before['request_id'],'started_at':before['started_at']},'completed_at':before['completed_at'],'artifact':artifact}}],'delivery':'not_required'},'recurrence_id')
 observation=domain('constellation.m2.observation/v1',j({'artifact_id':before['artifact_id'],'run_id':identity['run_id']}))
 pulse_cfg=support_enrollment(before,inputs['inputs_id'],observation,'before')
 support=pathlib.Path('/usr/bin/pulse-m2-support-resolver');os.environ['PULSE_M2_SUPPORT_CONFIG']=str(pulse_cfg)
 genesis={'campaign':identity['campaign'],'occurrence':identity['occurrence'],'program':domain('constellation.m2.program/v1',j({'unit':UNIT,'subject':subject,'scenario':'one governed start, independent postconditions'})),'expected_ag_work':work,'residuals':[],'budget':{'retry_limit':0,'retries_used':0,'probe_limit':1,'probes_used':0,'escalation_limit':0,'escalations_used':0}}
 proposal_input={'observation':observation,'proposal':{'schema':'ag.governed-loop.exact-work-proposal/v1','campaign':identity['campaign'],'subject':subject,'scope':scope,'work_schema':WORK,'work':work,'repair':None},'class':'initial'}
 cycle_slot=seal({'schema':'nightshift.recurrence_slot.v1','policy_id':policy['policy_id'],'configuration_version':identity['run_id'],'subject_id':before['subject']['id'],'scope_id':scope,'scheduler_clock_id':'m2-vm-utc','nominal_due_at':before['started_at'],'latest_admissible':{'scheduler_clock_id':'m2-vm-utc','at':stamp(t+datetime.timedelta(seconds=30))},'occurrence':0,'trigger':'scheduled'},'slot_id')
 request=seal({'schema':'nightshift.canonical_cycle_request.v1','slot':cycle_slot,'scheduler_clock_id':'m2-vm-utc','evaluated_at':stamp(t),'observation_id':observation,'policy':policy,'inputs':inputs,'recurrence':recurrence,'proposal':{'schema':'nightshift.precompiled_workflow_proposal.v2','workflow_id':'constellation-m2-service-start','intent_kind':'start_exact_inactive_unit','subject_digest':subject,'immutable_parameters':{'unit':UNIT,'target_machine_identity':plan['systemd_machine_identity']},'ag_executor_plan':plan,'campaign_id':identity['campaign'],'occurrence_id':identity['occurrence'],'mode':{'genesis':{'genesis':genesis}},'proposal_input':proposal_input}},'request_id')
 write(CONF/'cycle.json',request)
 provenance=run(['nq','--config',CONF/'nq.toml','--json','diagnostics','qualify',before['artifact_id']],'before-provenance')
 source=provenance['source']['source_id']
 nsargs=['nightshift','--store',ROOT/'nightshift.sqlite','cycle','run','--request',CONF/'cycle.json','--present-evidence-resolver',support,'--nq-program','/usr/bin/nq','--nq-config',CONF/'nq.toml','--nq-source-id',source,'--ag-loopctl','/usr/bin/ag-loopctl','--ag-database',database,'--ag-observation-resolver',CONF/'observation-resolver','--ag-observation-resolver-id','constellation-m2-observation/v1','--ag-runtime-profile',CONF/'runtime-profile.json']
 run(nsargs,'nightshift-cycle')
 gate=['--catalog',CONF/'catalog.json','--observation-resolver',CONF/'observation-resolver','--expected-observation-resolver-id','constellation-m2-observation/v1','--standing-resolver',CONF/'ag-standing-resolver','--expected-standing-resolver-id','constellation-m2-ag-standing/v1','--max-standing-ttl-ms','60000']
 run(['ag-loopctl','require-standing','--database',database],'ag-standing-required')
 run(['ag-loopctl','decide','--database',database]+gate,'ag-decision')
 authorized=run(['ag-loopctl','authorize','--database',database]+gate,'ag-authorization')
 def issuance(v):
  if isinstance(v,dict):
   if v.get('schema')=='ag.governed-loop.issuance/v1':return v
   for a in v.values():
    got=issuance(a)
    if got:return got
  return None
 issued=issuance(authorized)
 if not issued:raise RuntimeError('no authoritative issuance in product state')
 # This explicit operator-owned projection is installed only for the one spent issuance.
 issued_at=ms(now());standing=domain('constellation.m2.execution-standing/v1',j({'principal':'constellation-m2-release-operator','generation':identity['run_id'],'issuance':issued['issuance']}))
 resolution={'schema':'docket.governed-loop.execution-standing-resolution/v1','execution_standing':standing,'issuance':issued['issuance'],'campaign':issued['key']['campaign'],'occurrence':issued['key']['occurrence'],'subject':issued['subject'],'scope':issued['scope'],'status':'current','resolved_at_unix_ms':issued_at,'expires_at_unix_ms':issued_at+60000}
 resolution['currentness']=domain('constellation.m2.execution-standing-currentness/v1',j(resolution));resolution['resolution']=domain('constellation.m2.execution-standing-resolution/v1',j(resolution))
 write(CONF/'execution-standing.json',{'schema':'docket.owner-execution-standing-projection/v1','principal':'constellation-m2-release-operator','generation':identity['run_id'],'resolution':resolution})
 write('/usr/bin/docket-standing-resolver.enrollment.json',{'schema':'docket.execution-standing-enrollment/v1','principal':'constellation-m2-release-operator','projection':str(CONF/'execution-standing.json')})
 docket=['--docket','/usr/bin/docket','--docket-state',ROOT/'docket','--docket-trust',CONF/'trust.json','--docket-standing-resolver','/usr/bin/docket-standing-resolver','--executor',EFFECTD,'--executor-config',CONF/'plan.json','--issuer-principal','constellation-m2-release-operator','--issuer-key-id','m2-'+identity['run_id'],'--issuer-key',CONF/'private/issuer.pk8']
 run(['ag-loopctl','dispatch','--database',database]+docket,'ag-dispatch')
 settled=run(['ag-loopctl','poll','--database',database]+docket,'ag-settlement')
 inspection=run(['docket','governed-loop','inspect','--state',ROOT/'docket','--issuance',issued['issuance']],'docket-inspection')
 record=inspection['record']
 if record['status']!='settled' or record['settlement']['outcome']!='success':raise RuntimeError('Docket did not settle success')
 after=collect('systemd_unit','target-after')
 if after['outcome']['condition']!='explicitly_absent':raise RuntimeError('fresh target postcondition is not independently established')
 result={'schema':'constellation.m2.target-result/v1','run_id':identity['run_id'],'campaign':identity['campaign'],'occurrence':identity['occurrence'],'runtime_profile':profile_id,'work':work,'issuance':issued['issuance'],'attempt':record['custody']['attempt'],'ag_spend':record['custody']['ag_spend'],'settlement':record['settlement']['settlement'],'receipt':record['settlement']['receipt'],'before':before['artifact_id'],'target_after':after['artifact_id'],'scope':scope,'subject':subject,'completed_at':stamp(),'status':'target_path_passed','controller_result_required':True}
 write(ROOT/'target-result.json',result);print(j(result).decode())

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['prepare-target','prepare-controller','run-target','observe-controller']);parser.add_argument('--run-id');parser.add_argument('--subject');parser.add_argument('--endpoint');args=parser.parse_args()
 if os.geteuid()!=0:raise SystemExit('run as the admitted VM release operator (root)')
 try:
  if args.operation=='prepare-target':prepare_target(args.run_id)
  elif args.operation=='prepare-controller':
   ROOT.mkdir(mode=0o755,exist_ok=True);CONF.mkdir(mode=0o755,exist_ok=True);pathlib.Path('/run/constellation-m2/helpers').mkdir(mode=0o711,parents=True,exist_ok=True);subject=read(args.subject);write(ROOT/'subject.json',subject);nqconfig('http_endpoint',subject,args.endpoint)
  elif args.operation=='observe-controller':
   a=collect('http_endpoint','controller-after')
   if a['outcome']['condition']!='explicitly_absent':raise RuntimeError('controller HTTP postcondition is not established')
   inputs=digest({'schema':'constellation.m2.http-inputs/v1','artifact_id':a['artifact_id']});observation=domain('constellation.m2.http-observation/v1',j({'artifact_id':a['artifact_id']}))
   cfg=support_enrollment(a,inputs,observation,'controller-after')
   q=seal({'schema':'nightshift.present_evidence_query.v1','observation_cycle_id':'controller-'+read(ROOT/'subject.json')['fixture_run_id'],'request_nonce':str(uuid.uuid4()),'observation_id':observation,'diagnostic_inputs_id':inputs,'subject_id':a['subject']['id'],'scope_id':a['subject']['scope']['digest'],'artifact_ids':[a['artifact_id']]},'query_id')
   write(ROOT/'controller-query.json',q)
   support=run(['pulse-m2-support','resolve','--config',cfg],'controller-support',input_bytes=j(q))
   if support['standing']!='current':raise RuntimeError('fresh HTTP support is not current')
   result={'schema':'constellation.m2.controller-result/v1','run_id':read(ROOT/'subject.json')['fixture_run_id'],'artifact_id':a['artifact_id'],'support':support,'status':'controller_path_passed','completed_at':stamp()};write(ROOT/'controller-result.json',result);print(j(result).decode())
  else:run_target()
 except Exception as e:raise SystemExit(str(e))
