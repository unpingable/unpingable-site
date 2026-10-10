# Earlier repeat-refusal case — L

This is an earlier agent-driven session on archive 279fabef, separate from final session N on archive 0bdea16e. It was not re-run on N. No human ran this qualification. The following commands are exact recorded subcommand excerpts; surrounding directory changes and timing wrappers are omitted. Every result below exited 2. No current or successor package behavior is inferred.

The first command attempted a second preparation after an attempt already existed. The second attempted another native campaign initialization. The remaining commands were attempted after those refusals; the facade reported that `ag-loopctl` refused the command, without exposing a more specific native reason here. This is not proof that a second grant use reached the grant-use bound.

## prepare

```sh
sudo python3 scripts/native-action.py prepare --prestate inactive --assessment 'Current native evidence shows the enrolled unit inactive; cause is not established.'
```

```json
{"owner":"Operational ECAD","reason":"ATTEMPT_ALREADY_EXISTS","schema":"operational_ecad.refusal/v1"}
```

## init

```sh
sudo python3 scripts/native-action.py init
```

```json
{"owner":"Operational ECAD","reason":"CAMPAIGN_ALREADY_EXISTS","schema":"operational_ecad.refusal/v1"}
```

## record-proposal

```sh
sudo python3 scripts/native-action.py record-proposal
```

```json
{"owner":"Operational ECAD","reason":"NATIVE_COMMAND_REFUSED:ag-loopctl","schema":"operational_ecad.refusal/v1"}
```

## require-standing

```sh
sudo python3 scripts/native-action.py require-standing
```

```json
{"owner":"Operational ECAD","reason":"NATIVE_COMMAND_REFUSED:ag-loopctl","schema":"operational_ecad.refusal/v1"}
```

## decide

```sh
sudo python3 scripts/native-action.py decide
```

```json
{"owner":"Operational ECAD","reason":"NATIVE_COMMAND_REFUSED:ag-loopctl","schema":"operational_ecad.refusal/v1"}
```

## authorize

```sh
sudo python3 scripts/native-action.py authorize
```

```json
{"owner":"Operational ECAD","reason":"NATIVE_COMMAND_REFUSED:ag-loopctl","schema":"operational_ecad.refusal/v1"}
```

## dispatch

```sh
sudo python3 scripts/native-action.py dispatch
```

```json
{"owner":"Operational ECAD","reason":"NATIVE_COMMAND_REFUSED:ag-loopctl","schema":"operational_ecad.refusal/v1"}
```

The unit remained inactive in this earlier record. No reboot or prior-boot refusal is shown here. The missing `--identity` argument in the separate N session is argument validation, not an authority refusal.
