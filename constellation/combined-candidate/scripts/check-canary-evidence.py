#!/usr/bin/python3
"""Reference enrollment predicate: latest exact canary evaluation is current and active."""
import sys,json,datetime,pathlib
d=json.load(sys.stdin)
if not (d.get('schema')=='nq.evaluation_history.v1'):
    raise SystemExit('current exact canary evidence is unavailable')
records=[r for r in d['records'] if r.get('result',{}).get('context',{}).get('instance_id')=='svc-attention-canary']
if not (records):
    raise SystemExit('current exact canary evidence is unavailable')
envelope=max(records,key=lambda r:r['sequence'])['result']
ctx=envelope['context']; machine=pathlib.Path('/etc/machine-id').read_text().strip()
if not (ctx['subject']=='systemd-unit:'+machine+'/attention-canary.service'):
    raise SystemExit('current exact canary evidence is unavailable')
if not (ctx['scope']['value']['unit_name']=='attention-canary.service'):
    raise SystemExit('current exact canary evidence is unavailable')
if not (ctx['scope']['value']['machine_id']==machine):
    raise SystemExit('current exact canary evidence is unavailable')
if not (envelope['profile']['profile']=={'id':'nq.systemd_unit','version':2}):
    raise SystemExit('current exact canary evidence is unavailable')
if not (envelope['result']['state']=='explicitly_absent'):
    raise SystemExit('current exact canary evidence is unavailable')
at=datetime.datetime.fromisoformat(envelope['evaluated_at'].replace('Z','+00:00'))
if not (at.tzinfo is not None):
    raise SystemExit('current exact canary evidence is unavailable')
age=(datetime.datetime.now(datetime.timezone.utc)-at).total_seconds()
if not (-2<=age<60):
    raise SystemExit('current exact canary evidence is unavailable')
