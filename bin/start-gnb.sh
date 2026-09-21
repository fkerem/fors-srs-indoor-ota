#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirm-rf-reservation" ]]; then
    echo "Refusing to start RF without explicit reservation confirmation." >&2
    echo "Usage: $0 --confirm-rf-reservation" >&2
    exit 2
fi

PROFILE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
RUNTIME_DIR=/var/tmp/etc/ocudu
BASE_CONFIG="$RUNTIME_DIR/gnb_rf_x310_tdd_n78_40mhz.yml"
E2_CONFIG="$RUNTIME_DIR/gnb_e2.yml"
E2_ENV="$RUNTIME_DIR/e2-runtime.env"
GNB=/var/tmp/ocudu/build/apps/gnb/gnb

"$PROFILE_ROOT/bin/verify-profile-boundaries.sh"
[[ -x "$GNB" ]] || { echo "OCUDU gNB is not built at $GNB" >&2; exit 1; }
[[ -f "$BASE_CONFIG" ]] || { echo "Missing $BASE_CONFIG" >&2; exit 1; }
[[ -f "$E2_ENV" ]] || { echo "Missing $E2_ENV" >&2; exit 1; }

# Generated only from profile-validated booleans, IPv4 addresses, and integers.
# shellcheck source=/dev/null
source "$E2_ENV"

if [[ "$ENABLE_ORAN_E2" == "1" ]]; then
    "$PROFILE_ROOT/bin/preflight-e2.py" \
        --target "$ORAN_E2_TARGET_IP" \
        --port "$ORAN_E2_PORT" \
        --source "$ORAN_E2_BIND_IP"
    echo "E2 transport preflight passed; starting OCUDU with $ORAN_E2_AGENT_MODE agents."
    exec sudo "$GNB" -c "$BASE_CONFIG" -c "$E2_CONFIG"
fi

echo "Starting standalone OCUDU; E2 is disabled."
exec sudo "$GNB" -c "$BASE_CONFIG"
