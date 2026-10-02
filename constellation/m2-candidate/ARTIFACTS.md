# Exact rebuilt Jammy candidate

| Component | Forward SHA | Package | SHA256 |
|---|---|---|---|
| ag | `f21b2431d07e15e6d03298502c3ca29577c04058` | `agent-governor-ng-operator-tools_0.1.0+m2.20261001.2_amd64.deb` | `97bbddd8a3c2e70968c70f566a50d0038dbdc63aec35fb407129491805a5c307` |
| ag | `f21b2431d07e15e6d03298502c3ca29577c04058` | `agent-governor-ng-systemd-executor_0.1.0+m2.20261001.2_amd64.deb` | `1df6b1b49a89d70843bc70fa57ea6de4e5b01ce6040b6f65afbdb8b36ddfbc92` |
| docket | `0c771e9be75e6e4bb197ea355682ff86101de97f` | `constellation-docket_0.1.0+m2.20261001.2_amd64.deb` | `d17e4451884caed87da5d13f6af89aa53ebd95ea4faa444288742b37e2e75ced` |
| nightshift | `f891d88b2b0187284b0416a23ec6cb55c193c0f4` | `constellation-nightshift_0.1.0+m2.20261001.2_amd64.deb` | `10f032cd87c3d36f51fb07cf69cd976b9d0c0daa60369277f177a4b95bd68ce5` |
| nq | `623a74760c5ea02c633aa97bdb15d52953e66616` | `nq-ng_0.2.0_amd64.deb` | `b54f45658c8adb42c938a9fe91aaeabbb9f0c79d05c78fd2b9e5eff061331e3a` |

Five packages / fourteen executables built from exact published forward exports with pinned Ubuntu22.04/Rust1.94. All library/loader dependencies resolve; GLIBC <=2.35. Source-free archive inspection/installation entry point is in [RUNBOOK.md](RUNBOOK.md). Candidate is blocked only on [temporal authority](M2-CLOCK-DECISION.md); no fresh VM showing or Alpha2 acceptance is claimed.
