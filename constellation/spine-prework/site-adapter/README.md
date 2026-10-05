# Reference Nightshift observation adapter

This is installed reference glue, not a new core API. Its exact files are
frozen in the bundle manifest. The current changed-cone qualification uses
these files on Ubuntu22.04 with NQ0.2.4 and schema13. See the final lifecycle
receipt for actual current results; preparation alone is not acceptance.

Each timer tick reads the newest local diagnostic artifact for the enrolled
watcher, exports its native bytes, seals a canonical Nightshift cycle request,
and runs the ordinary packaged cycle. The internal SQLite read is unsupported
as a general API and explicitly refuses other schema versions.

Install scripts under `/usr/local/lib/nightshift/`, the provided service
drop-in under `/etc/systemd/system/nightshift-observation-cycle.service.d/`,
and the environment template as `/etc/nightshift/observation-cycle.env`.
Use the current artifact's actual producer.node_id as NIGHTSHIFT_NQ_SOURCE_ID;
a store replacement requires that value to change. `/var/lib/nightshift`
and its cycles directory are owned by nq, mode0750 in this reference layout.
The nq account also owns the Nightshift book here; a separately owned
consumer/ACL deployment is not qualified by this adapter.

The filesystem-capacity profile has no corresponding live support family.
The resolver answers unknown and Nightshift reports
`Incomplete (support_not_current)` honestly. That does not imply failed
acquisition or absent recurrence, and it must not be rewritten as healthy
support. The first slot is record_missing; following ordinary timer ticks
retain recurrence history. This profile makes no proposal and sets no AG,
continuity or substrate-origin flags.

Do not overwrite another deployment's store. Alternate paths require matching
the environment, unit read/write paths and operator metrics/status projections.
Follow DAY-TWO-RUNBOOK.md for fresh generation, archive and rollback.
