#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "usage: $0 LAN_IP SHARED_CIDR GATEWAY" >&2
    exit 2
fi

lan_ip=$1
shared_cidr=$2
gateway=$3

attempt=1
while (( attempt <= 120 )); do
    if ip -4 addr show | grep -Fq "${lan_ip}/"; then
        sudo ip route replace "$shared_cidr" via "$gateway"
        exit 0
    fi
    sleep 1
    ((attempt++))
done

echo "ERROR: gNB core-LAN address ${lan_ip} was not configured" >&2
exit 1
