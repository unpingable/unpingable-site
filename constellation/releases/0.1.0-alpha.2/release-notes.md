# Evaluate a saved check and hand attention to a local inbox

Constellation integration **0.1.0-alpha.2** fixes the
`saved-check-attention/v1` composition. It connects actual Monitor acquisition,
NQ saved SQLite evaluation and maintenance projection, Nightshift finite
recurrence and attention, and NQ local-file delivery custody.

Start with the [versioned guide](https://unpingable.com/constellation/releases/0.1.0-alpha.2/guide.html).
It includes exact public clones, builds, the provided external caller, retained
result inspection and recovery limits. No provider key or background service
is required. Supported test environment: Linux x86-64, Rust 1.94.0, Python 3.12
with SQLite, Git and a C compiler/linker. Runtime operation needs no network.

The example intentionally produces a failed check. Maintenance annotates that
failure; it does not erase it. One local inbox file is a real bounded handoff,
not human receipt or acknowledgment. Duplicate requests reuse retained custody;
changed receipt material refuses. Public-only reproduction and a separate
newcomer run passed, followed by read-only inspection with unchanged owner stores.

This is a finite, attended local example, not an installed application monitor.
It does not qualify live Slack/Discord, retention rollover, restoration,
cross-version migration, rollback, supervisor-loss recovery, or an injected
end-to-end uncertain delivery. Component-level uncertainty controls are labeled
separately in the [qualification record](https://unpingable.com/constellation/releases/0.1.0-alpha.2/qualification.json).

The [manifest](https://unpingable.com/constellation/releases/0.1.0-alpha.2/manifest.json)
pins only the components required here. Component versions remain independent;
alpha.1's consultation release is unchanged. AG/Docket action, the connected
cache tutorials, the full objective-read consumer journey, general ECAD/design
flow and federation are not part of this release. Qualifying this profile does
not complete those separate campaign deliverables.

Experimental alpha support is best effort with no guaranteed response time.
Use the [troubleshooting route](https://unpingable.com/constellation/troubleshooting.html)
with exact revisions and a minimal redacted excerpt, not credentials or whole
databases. Inspect existing custody before considering another attempt.
