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
- The UHD host and development packages are pinned to the tested 4.11 release;
  their installed versions are recorded in the build provenance.
- The gNB is never started by a startup service.
- The manual launcher requires `--confirm-rf-reservation`.
- The launcher probes the reserved X310's UHD/RFNoC compatibility and refuses
  to start RF if the radio image is incompatible.
- An incompatible X310 is never flashed or power-cycled automatically.
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

## X310/UHD mismatch recovery

The gNB launcher runs `uhd_usrp_probe --args type=x300` on its dedicated SDR
link before starting RF. If this fails, it stops before launching the gNB and
leaves the probe output in `/var/tmp/uhd-compat-probe.log`. Do not bypass the
probe by launching the gNB binary directly.

If the log reports an FPGA or RFNoC compatibility mismatch, first confirm the
allocated X310's identity, address, and FPGA flavor (HG or XG) against the
POWDER manifest and UHD discovery output. Do not infer the flavor from a prior
experiment. With explicit approval to change that allocated radio, obtain the
FPGA images matching the installed UHD version and verify the download:

```sh
sudo uhd_images_downloader --types x3xx_x310_fpga_default --test
```

Record the downloaded image's SHA-256 and the radio serial in the private run
evidence. Then load only the matching flavor onto the verified radio, without
requesting a separate firmware image load, substituting the confirmed address
and flavor:

```sh
sudo uhd_image_loader --args "type=x300,addr=<allocated-radio-ip>,fpga=<HG-or-XG>" --no-fw
```

Do not interrupt the image load. Power-cycle only that allocated X310 after a
successful load, then rerun `uhd_usrp_probe --args type=x300`. Start the gNB
only after that probe succeeds and the approved RF reservation is active. If
the device identity, image flavor, or approval is uncertain, stop and ask the
experiment owner or POWDER operator; do not guess or flash another radio.
