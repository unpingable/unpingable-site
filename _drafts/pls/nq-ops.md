# PLS draft — NQ (ops/SRE-facing)

**Status:** DRAFT, unpublished, unlinked. Operator-selected copy, 2026-07-16
tab intake. Graduation requires a coherence sweep against NQ at a named cut.
Killer sentence: *"The goal is not a smarter dashboard reader."*

---

## Why not just ask an AI what is happening?

You can already give an AI access to a shell, Prometheus, or Nagios and ask,
"What is happening on this server?"

It may give you a useful answer. But it will usually blur together several
different things:

- what the monitoring system actually observed;
- what data was missing, stale, or aggregated away;
- what the AI inferred from those observations;
- and what it merely recognized as a familiar failure pattern.

That is fine for exploration. It is not the same as a reliable report of
state.

This work adds the missing boundary. Instead of asking an AI to read
dashboards and produce a confident story, it produces bounded claims tied to
named evidence, collection time, authority, and known limits.

The result can say:

- what was directly observed;
- what conclusions the evidence supports;
- what remains uncertain or unobserved;
- and which actions, if any, are actually authorized.

Prometheus and Nagios collect signals. An AI can help interpret them. But
neither, by itself, gives downstream systems a state claim that can safely
survive automation, delegation, or dispute.

The goal is not a smarter dashboard reader. It is an operational reporting
layer whose claims can show their work.
