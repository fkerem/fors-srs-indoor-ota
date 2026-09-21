# OCUDU compatibility patches

No patch is enabled by default. The pinned `release_26_04` commit must be built
cleanly first.

If that build fails with a reviewed compatibility issue, copy only the
corresponding patch into this directory, preserve its original NIST notice,
record its source and SHA-256 here, and add an exact clean-application check to
`bin/deploy-ocudu.sh`. Never reference a patch in the local NIST testbed tree.
