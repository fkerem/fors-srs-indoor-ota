# OCUDU indoor-OTA Phase 2 peer

This fork extends the POWDER indoor-OTA profile with an optional private
shared-VLAN path to an O-RAN SC Near-RT RIC. It preserves standalone operation,
but replaces the legacy srsRAN Project checkout with the pinned formal OCUDU
`release_26_04` commit:

`050a2bb72e1d794cd60570d809987c1fcda3e54b`

## Safety properties

- The shared-VLAN name is blank by default and required only in E2 mode.
- OCUDU is built at the approved detached commit and its provenance is written
  to `/var/tmp/ocudu-build-provenance.txt`.
- The gNB is never started by a startup service.
- The manual launcher requires `--confirm-rf-reservation`.
- E2 mode must pass route/source validation and a payload-free SCTP
  connect/close before the gNB can start.
- No file or symlink may resolve outside this profile repository.
- The local NIST testbed is reference material only and is not a dependency.

## E2 modes

`du-only` is the initial evidence mode. It enables the DU E2 agent, E2SM-KPM,
E2SM-RC, and E2AP PCAP capture. `all` additionally enables CU-CP and CU-UP;
each association must be tracked as a separate logical E2 node.

Before parameterization, create the owner O-RAN experiment and discover its
live E2Term SCTP NodePort. Use a fresh random alphanumeric shared-VLAN name and
do not commit it.
