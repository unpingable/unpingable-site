# Connected-cache C input preparation

This release-local helper creates the two closed input documents used by the
published Maude C driver. It is derived from the public helper in
`constellation/examples/connected_cache`, with the Maude pin changed to the
post-teardown qualification revision named in this release. It measures exact
caller-selected files and creates fresh documents. It does not acquire an
observation, make a model request, authorize work, create a permission, or
run Docker.

Use an absent, caller-owned output directory and clean detached source
checkouts at the revisions in `../manifest.json`. The helper refuses a dirty or
wrong source checkout, symlink program inputs, changing inputs, invalid labels,
or a non-`sha256:` role digest. Keep the resulting input documents, exact source
revisions, executable hashes, and the manager record for later inspection.

The synthetic role digest and the development same-identity flag accepted by
the Maude preparation step are explicit fixture assertions. They do not prove
external provenance, authorize a later occurrence, or describe a deployable
Standing service.
