# Recorded terminal cycle — final N candidate

8 October 2026 agent-driven local guest qualification, final archive 0bdea16e, Workbench 10ea2d5. Guest label [REDACTED]. Commands below are exact executed subcommand excerpts; surrounding directory changes, echo statements and timestamps are omitted. Output state fragments are cited evidence selections, not reconstructed CLI output.

The unit was stopped deliberately for this run. This was an agent-driven local qualification, not a human usability trial. The command excerpts do not establish who authorizes: every invocation uses `sudo`; `agent-preflight` is a self-supplied preparation token, not authentication.

The screenshots are offline recorded pages. The amber banner was added at capture. “Operational EDA” is the recorded UI breadcrumb; “Operational ECAD” is the owner/schema naming in the receipts. The capture preserves those original labels.

## Initial native observation

Verbatim recorded summary line:

> status line: nginx.service: inactive (dead), observed 2 s ago, current boot. Unit state only, not service health.

Source: N03-broken-summary.txt line 1. It describes unit state, not HTTP health.

## prepare without --identity is rejected (argument validation)

```sh
sudo python3 scripts/native-action.py prepare --prestate inactive --assessment 'Current native evidence shows the enrolled unit inactive; cause is not established.'
```

```text
native-action.py: error: prepare requires an explicit --identity naming who drives it: a short token of letters, digits and ._@- (at most 64)
```

```text
[no-identity exit 2]
```

## prepare

```sh
sudo python3 scripts/native-action.py prepare --identity agent-preflight --prestate inactive --assessment 'Current native evidence shows the enrolled unit inactive; cause is not established.'
```

Selected schema field value (all other members omitted; this is not a standalone JSON document):

```text
"schema":"operational_ecad.fresh_preparation/v1"
```

Source: N04-governed-start.txt line 13, JSON pointer `/schema`.

Recorded command exit: `[exit 0]`.

## init

`init` creates the native campaign in an observation-required state. It declares that requirement; it does not itself request or perform collection.

```sh
sudo python3 scripts/native-action.py init
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"observation_required":
```

Source: N04-governed-start.txt line 19, JSON pointer `/native/state/observation_required`.

Recorded command exit: `[exit 0]`.

## record-proposal

```sh
sudo python3 scripts/native-action.py record-proposal
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"proposal_recorded":
```

Source: N04-governed-start.txt line25, JSON pointer `/native/state/proposal_recorded`.

Recorded command exit: `[exit 0]`.

## require-standing

```sh
sudo python3 scripts/native-action.py require-standing
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"standing_required":
```

Source: N04-governed-start.txt line31, JSON pointer `/native/state/standing_required`.

Recorded command exit: `[exit 0]`.

## decide

```sh
sudo python3 scripts/native-action.py decide
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"admissible_pending_authorization":
```

Source: N04-governed-start.txt line37, JSON pointer `/native/state/admissible_pending_authorization`.

Recorded command exit: `[exit 0]`.

## authorize

```sh
sudo python3 scripts/native-action.py authorize
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"authorization_consumed":
```

Source: N04-governed-start.txt line43, JSON pointer `/native/state/authorization_consumed`.

Recorded command exit: `[exit 0]`.

## dispatch

```sh
sudo python3 scripts/native-action.py dispatch
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"dispatched":
```

Source: N04-governed-start.txt line49, JSON pointer `/native/state/dispatched`.

Recorded command exit: `[exit 0]`.

## poll

```sh
sudo python3 scripts/native-action.py poll
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"settled_observation_required":
```

Source: N04-governed-start.txt line55, JSON pointer `/native/state/settled_observation_required`.

Recorded command exit: `[exit 0]`.

## continue

After dispatch and settlement, `continue` opens a new observation-required cycle with no inherited authority. It does not request collection. `complete` checks fresh active-unit evidence collected independently by NQ. The repeated `observation_required` branch is the successor cycle, not another initialization.

```sh
sudo python3 scripts/native-action.py continue
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"observation_required":
```

Source: N04-governed-start.txt line61, JSON pointer `/native/state/observation_required`.

Recorded command exit: `[exit 0]`.

## complete

```sh
sudo python3 scripts/native-action.py complete
```

Selected literal JSON fragment: this is the key of the **active enum branch** at the cited state pointer. The whole branch value and all other members are omitted; this is not a standalone JSON document or a Boolean value.

```text
"completed":
```

Source: N04-governed-start.txt line67, JSON pointer `/native/state/completed`.

Recorded command exit: `[exit 0]`.
