#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
    echo "Usage: $0 COMMIT ENABLE_E2 TARGET_IP TARGET_PORT AGENT_MODE" >&2
    exit 2
fi

COMMIT_HASH=$1
ENABLE_ORAN_E2=$2
ORAN_E2_TARGET_IP=$3
ORAN_E2_PORT=$4
ORAN_E2_AGENT_MODE=$5
PROFILE_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
source "$PROFILE_ROOT/bin/common.sh"

APPROVED_COMMIT=050a2bb72e1d794cd60570d809987c1fcda3e54b
OCUDU_DIR="$SRCDIR/ocudu"
RUNTIME_DIR="$SRCDIR/etc/ocudu"
PROVENANCE="$SRCDIR/ocudu-build-provenance.txt"

"$PROFILE_ROOT/bin/verify-profile-boundaries.sh"

[[ "$COMMIT_HASH" == "$APPROVED_COMMIT" ]] || {
    echo "ERROR: unapproved OCUDU commit: $COMMIT_HASH" >&2
    exit 1
}
[[ "$ENABLE_ORAN_E2" == "0" || "$ENABLE_ORAN_E2" == "1" ]] || exit 2
[[ "$ORAN_E2_AGENT_MODE" == "du-only" || "$ORAN_E2_AGENT_MODE" == "all" ]] || exit 2

if [[ ! -d "$OCUDU_DIR/.git" ]]; then
    sudo add-apt-repository -y ppa:ettusresearch/uhd
    sudo apt-get update
    sudo apt-get install -y \
        backward-cpp cmake gcc g++ iperf3 libboost-dev libfftw3-dev \
        libgtest-dev libmbedtls-dev libsctp-dev libuhd-dev libyaml-cpp-dev \
        make numactl pkg-config ppp uhd-host

    git clone --no-checkout "$OCUDU_REPO" "$OCUDU_DIR"
    git -C "$OCUDU_DIR" checkout --detach "$COMMIT_HASH"
fi

ACTUAL_COMMIT=$(git -C "$OCUDU_DIR" rev-parse HEAD)
[[ "$ACTUAL_COMMIT" == "$COMMIT_HASH" ]] || {
    echo "ERROR: OCUDU HEAD $ACTUAL_COMMIT does not match $COMMIT_HASH" >&2
    exit 1
}
if git -C "$OCUDU_DIR" symbolic-ref -q HEAD >/dev/null; then
    echo "ERROR: OCUDU checkout is attached to a branch" >&2
    exit 1
fi
git -C "$OCUDU_DIR" diff --quiet
git -C "$OCUDU_DIR" diff --cached --quiet
UNTRACKED_SOURCE=$(git -C "$OCUDU_DIR" ls-files --others --exclude-standard | \
    grep -v '^build/' || true)
[[ -z "$UNTRACKED_SOURCE" ]] || {
    echo "ERROR: OCUDU checkout contains untracked source files:" >&2
    echo "$UNTRACKED_SOURCE" >&2
    exit 1
}

if [[ ! -x "$OCUDU_DIR/build/apps/gnb/gnb" ]]; then
    cmake -S "$OCUDU_DIR" -B "$OCUDU_DIR/build" \
        -DENABLE_EXPORT=ON -DBUILD_TESTS=OFF
    cmake --build "$OCUDU_DIR/build" --parallel "$(nproc)"
fi

mkdir -p "$RUNTIME_DIR"
cp "$PROFILE_ROOT/etc/ocudu/gnb_rf_x310_tdd_n78_40mhz.yml" "$RUNTIME_DIR/"
cp "$PROFILE_ROOT/etc/ocudu/gnb_e2.yml" "$RUNTIME_DIR/"

LANIF=$(ip -j route show 192.168.1.0/24 | python3 -c \
    'import json,sys; routes=json.load(sys.stdin); print(routes[0]["dev"] if routes else "")')
LANIP=$(ip -j address show dev "$LANIF" | python3 -c \
    'import json,sys; data=json.load(sys.stdin); print(next(a["local"] for a in data[0]["addr_info"] if a["family"] == "inet"))')
[[ -n "$LANIF" && -n "$LANIP" ]] || { echo "ERROR: 192.168.1.0/24 interface not ready" >&2; exit 1; }

IPLAST=${LANIP##*.}
sed -i \
    -e "s/LANIP/$LANIP/g" \
    -e "s/GNBID/$IPLAST/g" \
    "$RUNTIME_DIR/gnb_rf_x310_tdd_n78_40mhz.yml"

if [[ "$ORAN_E2_AGENT_MODE" == "all" ]]; then
    E2_ENABLE_CU_CP=true
    E2_ENABLE_CU_UP=true
else
    E2_ENABLE_CU_CP=false
    E2_ENABLE_CU_UP=false
fi

sed -i \
    -e "s/E2_ENABLE_DU/true/g" \
    -e "s/E2_ENABLE_CU_CP/$E2_ENABLE_CU_CP/g" \
    -e "s/E2_ENABLE_CU_UP/$E2_ENABLE_CU_UP/g" \
    -e "s/E2_TARGET_IP/$ORAN_E2_TARGET_IP/g" \
    -e "s/E2_BIND_IP/$LANIP/g" \
    -e "s/E2_TARGET_PORT/$ORAN_E2_PORT/g" \
    "$RUNTIME_DIR/gnb_e2.yml"

cat >"$RUNTIME_DIR/e2-runtime.env" <<EOF
ENABLE_ORAN_E2=$ENABLE_ORAN_E2
ORAN_E2_TARGET_IP=$ORAN_E2_TARGET_IP
ORAN_E2_PORT=$ORAN_E2_PORT
ORAN_E2_BIND_IP=$LANIP
ORAN_E2_AGENT_MODE=$ORAN_E2_AGENT_MODE
EOF
chmod 0600 "$RUNTIME_DIR/e2-runtime.env"

GNB_VERSION=$("$OCUDU_DIR/build/apps/gnb/gnb" --version 2>&1 || true)
cat >"$PROVENANCE" <<EOF
repository=$OCUDU_REPO
release=release_26_04
commit=$ACTUAL_COMMIT
head_mode=detached
source_tree_clean=true
cmake_options=-DENABLE_EXPORT=ON -DBUILD_TESTS=OFF
patches=none
gnb_version=$GNB_VERSION
EOF

touch "$SRCDIR/ocudu-setup-complete"
echo "OCUDU setup complete. RF was not started."
