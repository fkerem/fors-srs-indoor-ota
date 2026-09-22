#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "usage: $0 VLAN_IP LAN_IP SHARED_CIDR" >&2
    exit 2
fi

vlan_ip=$1
lan_ip=$2
shared_cidr=$3

wait_for_address() {
    local address=$1
    local attempt

    attempt=1
    while (( attempt <= 120 )); do
        if ip -4 addr show | grep -Fq "${address}/"; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done

    echo "ERROR: address ${address} was not configured" >&2
    return 1
}

wait_for_address "$vlan_ip"
wait_for_address "$lan_ip"

sudo sysctl -w net.ipv4.ip_forward=1
if ! sudo modprobe nf_conntrack_sctp; then
    echo "WARNING: nf_conntrack_sctp is unavailable; continuing with SCTP forwarding" >&2
fi

if ! sudo iptables -t nat -C POSTROUTING -s 192.168.1.0/24 \
    -d "$shared_cidr" -j MASQUERADE; then
    sudo iptables -t nat -A POSTROUTING -s 192.168.1.0/24 \
        -d "$shared_cidr" -j MASQUERADE
fi
