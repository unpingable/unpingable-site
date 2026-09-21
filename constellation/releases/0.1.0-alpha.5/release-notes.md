# Constellation integration 0.1.0-alpha.5

Exercise one installed-cadence saved-check tick against a disposable local
queue, retain the exact Nightshift evaluation and NQ local-file delivery, then
verify same-slot replay, overlap refusal, and missed-slot no-catch-up behavior.

Start with the [pinned guide](https://unpingable.com/constellation/releases/0.1.0-alpha.5/guide.html).
The manifest fixes NQ at `9d00030ba8777fbd80286c340a72797cbf74315d`
and Nightshift/Monitor at public commit
`d9a0976fad133311c3f8cd5fc780f035714c17c7`. That revision preserves the
attention-clock precision needed by the local example.

The disposable single-user example builds NQ in debug mode under its explicit
debug-only same-UID helper exception. This is a local substitution fixture, not
an installed identity boundary. Nightshift and Monitor remain locked release
builds; an installed NQ release build requires a distinct enrolled helper
account.

Alpha.5 passed a clean public-only anonymous-clone reproduction: exact NQ,
Nightshift and Monitor commits were cloned and checked out; the builds and
direct disposable tick completed; retained owner records were inspected by a
fresh process. The qualification record binds the execution identity and result
summary digest. It does not turn a retained result into a present-condition
claim.

This release exercises the installed-cadence composition by directly invoking
one tick; it does not install or activate systemd. It also does not establish
response-loss handling after NQ acceptance, live Slack or Discord delivery,
human receipt or acknowledgment, migration, restore, rollback, retention
rollover, or general unattended operation.

The earlier alpha.1 through alpha.4 releases remain unchanged. This release
does not synchronize component versions or extend the AG/Docket governed-action
path. Experimental support is best effort with no guaranteed response time.
