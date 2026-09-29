#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
    echo "Usage: $0 [probe-log-path]" >&2
    exit 2
fi

UHD_PROBE_LOG=${1:-/var/tmp/uhd-compat-probe.log}

# The profile's dedicated SDR link contains only its allocated X310. A failed
# probe must stop the launcher before it can invoke the RF-transmitting gNB.
if ! timeout 60 uhd_usrp_probe --args type=x300 >"$UHD_PROBE_LOG" 2>&1; then
    cat "$UHD_PROBE_LOG" >&2
    echo "ERROR: X310/UHD compatibility probe failed; RF was not started." >&2
    echo "Review $UHD_PROBE_LOG and the manual recovery steps in README.md." >&2
    exit 1
fi

echo "X310/UHD compatibility probe passed; log: $UHD_PROBE_LOG"
