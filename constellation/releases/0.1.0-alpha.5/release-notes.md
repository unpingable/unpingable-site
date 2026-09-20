# Constellation integration 0.1.0-alpha.5 candidate

Exercise one installed-cadence saved-check tick against a disposable local
queue, retain the exact Nightshift evaluation and NQ local-file delivery, then
verify same-slot replay, overlap refusal, and missed-slot no-catch-up behavior.

Start with the [pinned candidate guide](https://unpingable.com/constellation/releases/0.1.0-alpha.5/guide.html).
The manifest fixes NQ at `9d00030ba8777fbd80286c340a72797cbf74315d`
and Nightshift/Monitor at
`e54acd83af9827bb60d543b157a833d7aa849f5e`. The latter is the local candidate
commit based on public `ef7877f81d56706663e31ddfa4e05bb89aab5443` and adds
`examples/saved-check-installed-local.py`.

Qualification is pending. Do not describe alpha.5 as passed or released until
an independent clean reproduction can anonymously clone both repositories,
check out those exact commits, build locked dependencies, run the example, and
inspect its retained owner records. The qualification record names the required
observations.

This candidate exercises the installed-cadence composition by directly invoking
one tick; it does not install or activate systemd. It also does not establish
response-loss handling after NQ acceptance, live Slack or Discord delivery,
human receipt or acknowledgment, migration, restore, rollback, retention
rollover, or general unattended operation.

The earlier alpha.1 through alpha.4 releases remain unchanged. This candidate
does not synchronize component versions or extend the AG/Docket governed-action
path. Experimental support is best effort with no guaranteed response time.
