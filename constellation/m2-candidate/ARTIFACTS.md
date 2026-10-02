# M2 candidate artifacts

M2_RELEASE_CANDIDATE_BLOCKED_ON_OWNER_OR_PRODUCT_DECISION

| Component | Forward SHA | Package | SHA256 | Ubuntu 22.04 dependency status | M2 role |
|---|---|---|---|---|---|
| ag | `c297f850072eceb79dc4766363b32424b2db5246` | agent-governor-ng-operator-tools_0.1.0+m2.20261001_amd64.deb | `567846d21c34370bb9d3fcc3e6d43024666667515f6a940d968a004811b49572` | ELF dependencies resolved; no VM installation/effect | Authority / operator inspection / target executor |
| ag | `c297f850072eceb79dc4766363b32424b2db5246` | agent-governor-ng-systemd-executor_0.1.0+m2.20261001_amd64.deb | `4f2a1f15d9a93352777e1156378d61001a875b91725e8ce588cb172c9d7dcd9c` | ELF dependencies resolved; no VM installation/effect | Authority / operator inspection / target executor |
| docket | `f77be5193a5860d4809ea0c20dcc0fd1cd7d1f8e` | constellation-docket_0.1.0+m2.20261001_amd64.deb | `92ac963d6c43587c3a331703535370796355e53fbfa248eef1849e56e75a7879` | ELF dependencies resolved; no VM installation/effect | Attempt custody and reconciliation |
| nq | `f34542ecc754ad3a85e253818dfd635d7fe7482d` | nq-ng_0.2.0_amd64.deb | `53744651bc8af63101fd810ce4ed1da7636a314537c117c4ff9bcf41b42ddbe0` | ELF dependencies resolved; no VM installation/effect | Independent systemd and HTTP observations |
| nightshift | `eda8f37abce68011469b06d699bb8a12a5896e94` | constellation-nightshift_0.1.0+m2.20261001_amd64.deb | `fd3c6f62a3ff57dbf400232a364154d4edaf5a074e9dfe8573837079355d0247` | ELF dependencies resolved; no VM installation/effect | Temporal evidence and proposal binding |

Exact runtime executable identities and dependencies are in `candidate.json` and the archive’s `contracts/*-abi.json`. Build reproduction is not claimed. The source-free archive is retained by the release owner; it is not a promoted GitHub release. See [RUNBOOK.md](RUNBOOK.md) for blockers, inputs and exclusions.
