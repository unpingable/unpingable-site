#!/usr/bin/python3
"""Reference v1 owner enrollment on one host (root). Each subcommand writes one
owner-controlled layer and prints the identities it created as IDENT lines."""
import base64, hashlib, json, os, pathlib, subprocess, sys, time

UNIT = 'attention-canary.service'
INSTANCE = 'svc-attention-canary'
SITE = os.environ.get('SITE', 'reference')
WINDOW = int(os.environ.get('WINDOW_SECONDS', '300'))
MAX_AGE = int(os.environ.get('RESOLVER_MAX_AGE_MS', '90000'))
MANDATE_HOURS = int(os.environ.get('MANDATE_HOURS', '24'))
WORK = 'ag-effectd.docket-executor-systemd-work/v2'
ETC = pathlib.Path('/etc/constellation-remediation')
VAR = pathlib.Path('/var/lib/constellation-remediation')
EFFECTD = '/usr/libexec/agent-governor-ng/ag-effectd'
GRANT_RESOLVER = '/usr/bin/docket-standing-grant-resolver'
PRINCIPAL = 'constellation-remediation-owner'
PRE_ID = 'constellation.remediation.unit-not-active/v1'
POST_ID = 'constellation.remediation.unit-active/v1'
STANDING_ID = 'constellation.remediation.ag-standing/v1'
NQCONF = '/etc/nq/nqd-ops.toml'
INBOX = '/var/lib/nq-ops-attention-test-inbox'


def j(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def raw(b):
    return 'sha256:' + hashlib.sha256(b).hexdigest()


def domain(d, b):
    d = d.encode()
    return raw(b'ag-ng\0digest\0v1\0' + len(d).to_bytes(16, 'big') + d + len(b).to_bytes(16, 'big') + b)


def write(path, data, mode=0o644):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else j(data))
    path.chmod(mode)


def read(path):
    return json.loads(pathlib.Path(path).read_bytes())


def run(argv, stdin=None):
    p = subprocess.run([str(a) for a in argv], input=stdin, capture_output=True)
    if p.returncode:
        raise SystemExit(f'{argv[0]} refused ({p.returncode}): ' + p.stderr.decode(errors='replace')[-2000:])
    return p.stdout


def ident(k, v):
    print(f'IDENT {k}={v}', flush=True)


def mid():
    return pathlib.Path('/etc/machine-id').read_text().strip()


def identity():
    m = mid()
    subject = domain('constellation.remediation.subject/v1', j({'machine_id': m, 'unit': UNIT}))
    scope = domain('constellation.remediation.scope/v1', j({'instance_id': INSTANCE, 'machine_id': m, 'site': SITE, 'unit': UNIT}))
    return m, subject, scope


def toml(v):
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        return '[' + ', '.join(toml(a) for a in v) + ']'
    if isinstance(v, dict):
        return '{ ' + ', '.join(f'{k} = {toml(a)}' for k, a in v.items()) + ' }'
    raise ValueError(v)


def table(name, d, array=False):
    head = f'[[{name}]]' if array else f'[{name}]'
    return head + '\n' + ''.join(f'{k} = {toml(v)}\n' for k, v in d.items()) + '\n'


def nq_config():
    if pathlib.Path(NQCONF).exists() or pathlib.Path(NQCONF).is_symlink():
        raise SystemExit('existing ops configuration: inspect it; fresh enrollment will not replace it')
    m = mid()
    out = ('schema = "nq.config.v1"\ndatabase_path = "/var/lib/nq-ops/nq.db"\nsocket_path = "/run/nq-ops/nqd.sock"\n'
           'admissions_dir = "/var/lib/nq-ops/admissions"\nhelper_runtime_dir = "/run/nq-ops/helpers"\n\n')
    out += '# Qualification notice route (local inbox) and the page route (network disabled by the evaluator).\n'
    out += table('notification_routes', {'reference': 'attention-test', 'transport': 'local_file',
                                         'local_inbox_directory': INBOX, 'timeout_ms': 10000, 'max_response_bytes': 1024}, True)
    out += table('notification_routes', {'reference': 'pagerduty-ops', 'transport': 'pagerduty',
                                         'routing_key_env': 'NQ_PAGERDUTY_OPS_ROUTING_KEY', 'timeout_ms': 10000,
                                         'max_response_bytes': 4096}, True)
    out += table('watchers', {'instance_id': INSTANCE, 'carrier': 'stdio', 'subject': f'systemd-unit:{m}/{UNIT}',
                              'capability_ceiling': ['read_systemd_unit'], 'checkpoint_policy': 'disabled'}, True)
    out += table('watchers.command', {'executable': '/usr/lib/nq/helpers/nq-host-resource-helper', 'args': [], 'env': {},
                                      'execution_account': 'nq-helper', 'working_directory': '/usr/lib/nq/helpers'})
    out += table('watchers.profile', {'id': 'nq.systemd_unit', 'version': 2})
    out += table('watchers.scope', {'kind': 'systemd_unit', 'value': {'schema': 'nq.systemd_unit_scope.v2', 'machine_id': m, 'unit_name': UNIT}})
    out += table('watchers.vantage', {'kind': 'local', 'value': {}})
    out += table('watchers.schedule', {'interval_seconds': int(os.environ.get('WATCH_INTERVAL', '30')), 'jitter_seconds': 0,
                                       'deadline_ms': 30000, 'retry_backoff_seconds': 10, 'max_retry_backoff_seconds': 60})
    out += table('watchers.resources', {'max_response_bytes': 1048576, 'max_stderr_bytes': 65536, 'max_observations': 1,
                                        'max_address_space_bytes': 536870912, 'max_cpu_seconds': 60, 'max_processes': 32,
                                        'max_open_files': 128, 'max_file_bytes': 67108864})
    write(NQCONF, out.encode(), 0o644)
    ident('nq.config_sha256', raw(out.encode()))
    ident('nq.watcher_subject', f'systemd-unit:{m}/{UNIT}')


def attention_config():
    if pathlib.Path('/etc/constellation-attention/attention.toml').exists() or pathlib.Path('/etc/constellation-attention/attention.toml').is_symlink():
        raise SystemExit('existing attention configuration: inspect it; fresh enrollment will not replace it')
    cfg = f'''schema = "constellation.attention_config.v1"
site = "{SITE}"
state_path = "/var/lib/constellation-attention/state.json"
command_timeout_seconds = 90

[nq]
program = "/usr/bin/nq"
config = "{NQCONF}"

[routes]
notice_route = "attention-test"
notice_transport = "local_file"
page_route = "pagerduty-ops"
network_enabled = false

[inputs.nq_status]
label = "nqd"
source = "evaluation_history"
command = ["/usr/bin/nq", "--config", "{NQCONF}", "--json"]
window_records = 300
max_age_seconds = 300
stale_after_seconds = 180

[[remediation.targets]]
rule = "service-down"
target_class = "{UNIT}"
policy = "auto_remediate_then_page"
window_seconds = {WINDOW}
'''
    write('/etc/constellation-attention/attention.toml', cfg.encode(), 0o644)
    ident('attention.config_sha256', raw(cfg.encode()))


def wrapper(path, body):
    write(path, ('#!/bin/sh\n' + body + '\n').encode(), 0o755)


def ag_docket():
    for existing in (ETC / 'runtime-profile.json', ETC / 'identity.json', ETC / 'private/issuer.pem', pathlib.Path(EFFECTD + '.deployment.json')):
        if existing.exists() or existing.is_symlink():
            raise SystemExit('existing action enrollment: preserve it and use the documented re-enrollment procedure')
    m, subject, scope = identity()
    for d, mode in ((ETC, 0o755), (ETC / 'resolvers', 0o755), (ETC / 'plans', 0o755), (ETC / 'private', 0o700),
                    (ETC / 'standing', 0o755), (VAR, 0o755), (VAR / 'consumer', 0o700), (VAR / 'ag', 0o700),
                    (VAR / 'docket', 0o700), (VAR / 'effect', 0o700), (VAR / 'grant-uses', 0o700)):
        d.mkdir(parents=True, exist_ok=True)
        d.chmod(mode)
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    keys = ETC / 'private'
    pem = keys / 'issuer.pem'
    if not pem.exists():
        run(['openssl', 'genpkey', '-algorithm', 'ED25519', '-out', pem])
    private = run(['openssl', 'pkey', '-in', pem, '-outform', 'DER'])
    public = run(['openssl', 'pkey', '-in', pem, '-pubout', '-outform', 'DER'])[-32:]
    if len(private) != 48 or private[:16].hex() != '302e020100300506032b657004220420':
        raise SystemExit('unexpected generated PKCS8 format')
    (keys / 'issuer.pk8').write_bytes(bytes.fromhex('3051020101300506032b657004220420') + private[-32:] + bytes.fromhex('812100') + public)
    for p in keys.iterdir():
        p.chmod(0o600)
    key_id = 'reference-' + run_id
    write(ETC / 'docket-trust.json', {'issuers': [{'issuer_principal': PRINCIPAL, 'key_id': key_id,
                                                   'public_key': base64.urlsafe_b64encode(public).decode().rstrip('=')}]})
    common = f'--config {NQCONF} --instance-id {INSTANCE} --unit {UNIT} --machine-id {m}'
    drop = 'exec /usr/bin/setpriv --reuid=nq --regid=nq --init-groups -- /usr/bin/constellation-nq-unit-resolver'
    wrapper(ETC / 'resolvers/unit-not-active', f'{drop} {common} --resolver-id {PRE_ID} --claim not-active --max-age-ms {MAX_AGE}')
    wrapper(ETC / 'resolvers/unit-active', f'{drop} {common} --resolver-id {POST_ID} --claim active --max-age-ms {MAX_AGE}')
    wrapper(ETC / 'resolvers/ag-standing', f'exec /usr/bin/ag-standing-resolver --mandate-store {ETC}/mandates.json '
                                           f'--resolver-id {STANDING_ID} --answer-ttl-ms 60000')
    basis = lambda claim: json.loads(run(['/usr/bin/constellation-nq-unit-resolver', '--print-basis', '--instance-id', INSTANCE,
                                          '--unit', UNIT, '--machine-id', m, '--claim', claim]))['basis']
    pre, post = basis('not-active'), basis('active')
    now_ms = int(time.time() * 1000)
    valid_until = now_ms + MANDATE_HOURS * 3600 * 1000
    write(ETC / 'mandates.json', {'schema': 'ag.governed-loop.standing-mandate-store/v1', 'mandates': [
        {'subject': subject, 'scope': scope, 'generation': 1, 'status': 'active', 'valid_until_unix_ms': valid_until}]})
    template = {'schema': 'ag-effectd.docket-executor-systemd-plan/v2', 'attempt_store': str(VAR / 'effect/attempts.sqlite'),
                'subject': subject, 'scope': scope, 'effect_index': 0,
                'effect': {'kind': 'systemd_unit', 'target': 'attention-canary', 'unit': UNIT, 'action': 'start',
                           'expected_active_state': 'inactive', 'expected_unit_file_state': 'enabled'},
                'file_policy': {'max_content_bytes': 1024, 'trusted_ancestor_uid': 0, 'trusted_parent_uid': 0,
                                'require_private_parent_writes': True},
                'systemd_machine_identity': m, 'execution_lock_timeout_ms': 5000, 'job_timeout_ms': 30000}
    write(ETC / 'plans/template.json', template)
    enrolled = json.loads(run(['ag-loopctl', 'systemd-plan-enrollment', '--template', ETC / 'plans/template.json',
                               '--unit', UNIT, '--prestate', 'inactive', '--prestate', 'failed']))
    write(ETC / 'plan-enrollment.json', enrolled)
    catalog = {'schema': 'ag.governed-loop.exact-work-catalog/v2', 'entries': {WORK: {
        'work_schema': WORK, 'subject': subject, 'scope': scope,
        'observation_basis': {'kind': 'typed_basis', 'requirement': pre},
        'admitted_plans': enrolled['admitted_plans'],
        'postcondition_basis': {'kind': 'typed_basis', 'requirement': post}}}}
    write(ETC / 'catalog.json', catalog)
    enrollment = {'schema': 'ag.governed-loop.runtime-profile-enrollment/v1', 'profile_label': 'constellation-bar-v1-' + run_id,
                  'observation_resolver': str(ETC / 'resolvers/unit-not-active'), 'observation_resolver_id': PRE_ID,
                  'standing_resolver': str(ETC / 'resolvers/ag-standing'), 'standing_resolver_id': STANDING_ID,
                  'max_standing_ttl_ms': 60000, 'exact_work_catalog': str(ETC / 'catalog.json'), 'controlling_review': None,
                  'docket': {'schema': 'ag.governed-loop.docket-root-enrollment/v1', 'docket_program': '/usr/bin/docket',
                             'state_directory': str(VAR / 'docket'), 'trust_config': str(ETC / 'docket-trust.json'),
                             'standing_resolver': GRANT_RESOLVER, 'executor_adapter': EFFECTD,
                             'issuer_principal': PRINCIPAL, 'issuer_key_id': key_id, 'issuer_key': str(keys / 'issuer.pk8')},
                  'human_verifier': None,
                  'postcondition_resolver': str(ETC / 'resolvers/unit-active'), 'postcondition_resolver_id': POST_ID}
    write(ETC / 'enrollment.json', enrollment)
    sealed = json.loads(run(['ag-loopctl', 'seal-runtime-profile', '--enrollment', ETC / 'enrollment.json',
                             '--output', ETC / 'runtime-profile.json']))
    profile_id = sealed.get('profile_digest') or domain('ag.governed-loop.runtime-profile/v1', j(read(ETC / 'runtime-profile.json')))
    write(pathlib.Path(EFFECTD).with_name('ag-effectd.deployment.json'),
          {'schema': 'ag-effectd.deployment/v1', 'campaign_database': str(VAR / 'ag/campaign.sqlite'),
           'expected_runtime_profile': profile_id})
    works = {}
    for pre_state in ('inactive', 'failed'):
        plan = json.loads(json.dumps(template))
        plan['effect']['expected_active_state'] = pre_state
        plan['authorization'] = {'expected_runtime_profile': profile_id}
        path = ETC / f'plans/start-{pre_state}.json'
        write(path, plan)
        works[pre_state] = run([EFFECTD, 'plan-id', path]).decode().strip()
    ident('machine_id', m)
    ident('ag.subject', subject)
    ident('ag.scope', scope)
    ident('ag.precondition_basis', json.dumps(pre, sort_keys=True))
    ident('ag.postcondition_basis', json.dumps(post, sort_keys=True))
    ident('ag.admitted_plans', json.dumps(enrolled['admitted_plans']))
    ident('ag.catalog_sha256', raw((ETC / 'catalog.json').read_bytes()))
    ident('ag.runtime_profile', profile_id)
    ident('ag.work.inactive', works['inactive'])
    ident('ag.work.failed', works['failed'])
    ident('ag.issuer_key_id', key_id)
    ident('ag.issuer_public_key_sha256', raw(public))
    ident('ag.mandate_valid_until_unix_ms', valid_until)
    write(ETC / 'identity.json', {'machine_id': m, 'subject': subject, 'scope': scope, 'runtime_profile': profile_id,
                                  'issuer_key_id': key_id, 'works': works, 'run_id': run_id})


def grant(name, max_uses, hours=24):
    max_uses, hours = int(max_uses), int(hours)
    if max_uses <= 0 or hours <= 0:
        raise SystemExit('grant limits must be positive')
    for path in (ETC / 'standing/grant.json', pathlib.Path(GRANT_RESOLVER + '.enrollment.json')):
        if path.exists() or path.is_symlink():
            raise SystemExit('existing grant enrollment: preserve or explicitly revoke/retire it before new enrollment')
    _, subject, scope = identity()
    now_ms = int(time.time() * 1000)
    journal = VAR / 'grant-uses' / name
    if journal.exists():
        raise SystemExit(f'journal {journal} exists; a new grant needs a new journal')
    journal.mkdir(mode=0o700)
    journal.chmod(0o700)
    g = {'schema': 'docket.owner-execution-standing-grant/v1', 'grant_id': f'reference-canary/{name}', 'principal': PRINCIPAL,
         'subject': subject, 'scope': scope, 'work_schema': WORK, 'not_before_unix_ms': now_ms - 60000,
         'expires_at_unix_ms': now_ms + int(hours) * 3600 * 1000, 'max_uses': int(max_uses), 'standing_ttl_ms': 60000,
         'revocation_marker': str(ETC / 'standing' / f'grant-{name}.revoked'), 'use_journal': str(journal)}
    data = json.dumps(g, indent=2, sort_keys=True).encode() + b'\n'
    write(ETC / 'standing/grant.json', data, 0o644)
    pin = raw(data)
    write(GRANT_RESOLVER + '.enrollment.json', {'schema': 'docket.execution-standing-grant-enrollment/v1',
                                                'principal': PRINCIPAL, 'grant': str(ETC / 'standing/grant.json'),
                                                'grant_sha256': pin})
    ident(f'grant.{name}.id', g['grant_id'])
    ident(f'grant.{name}.sha256', pin)
    ident(f'grant.{name}.max_uses', max_uses)
    ident(f'grant.{name}.expires_at_unix_ms', g['expires_at_unix_ms'])
    ident(f'grant.{name}.revocation_marker', g['revocation_marker'])
    ident(f'grant.{name}.use_journal', journal)


def mandate(hours):
    _, subject, scope = identity()
    valid_until = int(time.time() * 1000) + int(hours) * 3600 * 1000
    write(ETC / 'mandates.json', {'schema': 'ag.governed-loop.standing-mandate-store/v1', 'mandates': [
        {'subject': subject, 'scope': scope, 'generation': 1, 'status': 'active', 'valid_until_unix_ms': valid_until}]})
    ident('ag.mandate_valid_until_unix_ms', valid_until)


def consumer_config():
    if (ETC / 'consumer.toml').exists() or (ETC / 'consumer.toml').is_symlink():
        raise SystemExit('existing consumer configuration: preserve it')
    idn = read(ETC / 'identity.json')
    text = pathlib.Path('/etc/constellation-remediation/consumer.toml.example').read_text()
    text = text.replace('REPLACE-32-lowercase-hex', idn['machine_id']).replace('REPLACE-key-id', idn['issuer_key_id'])
    text = text.replace('site = "reference"', f'site = "{SITE}"')
    write(ETC / 'consumer.toml', text.encode(), 0o644)
    ident('consumer.config_sha256', raw(text.encode()))


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('owner enrollment requires root')
    if len(sys.argv) < 2 or sys.argv[1] not in ('nq-config', 'attention-config', 'ag-docket', 'consumer-config', 'mandate', 'grant'):
        raise SystemExit('usage: enroll-remediation.py nq-config|attention-config|ag-docket|consumer-config|mandate HOURS|grant NAME MAX_USES [HOURS]')
    cmd = sys.argv[1]
    if cmd == 'grant':
        if len(sys.argv) not in (4, 5) or not sys.argv[2].isalnum() or int(sys.argv[3]) <= 0 or (len(sys.argv) == 5 and int(sys.argv[4]) <= 0):
            raise SystemExit('grant needs an alphanumeric name and positive bounded max uses')
        grant(*sys.argv[2:])
        raise SystemExit(0)
    {'nq-config': nq_config, 'attention-config': attention_config, 'ag-docket': ag_docket,
     'consumer-config': consumer_config, 'mandate': lambda: mandate(sys.argv[2])}[cmd]()
