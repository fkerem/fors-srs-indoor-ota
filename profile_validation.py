#!/usr/bin/env python3

import ipaddress
import re


VLAN_NAME_RE = re.compile(r"^[A-Za-z0-9]{1,31}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
AGENT_MODES = {"du-only", "all"}


def shared_network_cidr(peer_ip, netmask):
    return str(ipaddress.IPv4Network("{}/{}".format(peer_ip, netmask), strict=False))


def validate_parameters(enable_e2, vlan_name, peer_ip, netmask, target_ip,
                        port, agent_mode, ocudu_commit, approved_commit):
    errors = []

    if agent_mode not in AGENT_MODES:
        errors.append(("oran_e2_agent_mode", "must be du-only or all"))

    if not COMMIT_RE.fullmatch(ocudu_commit or ""):
        errors.append(("ocudu_commit_hash", "must be a full lowercase 40-character commit hash"))
    elif ocudu_commit != approved_commit:
        errors.append(("ocudu_commit_hash", "must match the approved release_26_04 commit"))

    try:
        port_value = int(port)
        if not 20000 <= port_value <= 40000:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(("oran_e2_port", "must be an integer from 20000 through 40000"))

    try:
        peer = ipaddress.IPv4Address(peer_ip)
    except ValueError:
        peer = None
        errors.append(("oran_shared_vlan_ip", "must be a valid IPv4 address"))

    try:
        network = ipaddress.IPv4Network("{}/{}".format(peer_ip, netmask), strict=False)
    except ValueError:
        network = None
        errors.append(("oran_shared_vlan_netmask", "must form a valid IPv4 network with the peer address"))

    target = None
    if target_ip:
        try:
            target = ipaddress.IPv4Address(target_ip)
        except ValueError:
            errors.append(("oran_e2_target_ip", "must be a valid IPv4 address"))

    if enable_e2:
        if not VLAN_NAME_RE.fullmatch(vlan_name or ""):
            errors.append(("oran_shared_vlan_name", "must contain 1-31 alphanumeric characters when E2 is enabled"))
        if not target_ip:
            errors.append(("oran_e2_target_ip", "is required when E2 is enabled"))
        if peer is not None and network is not None and peer in (
                network.network_address, network.broadcast_address):
            errors.append(("oran_shared_vlan_ip", "must be a usable host address"))
        if target is not None and network is not None:
            if target not in network:
                errors.append(("oran_e2_target_ip", "must be in the shared-VLAN subnet"))
            elif target in (network.network_address, network.broadcast_address):
                errors.append(("oran_e2_target_ip", "must be a usable host address"))
        if peer is not None and target is not None and peer == target:
            errors.append(("oran_e2_target_ip", "must differ from the peer shared-VLAN address"))
    else:
        if vlan_name:
            errors.append(("oran_shared_vlan_name", "must be blank when E2 is disabled"))
        if target_ip:
            errors.append(("oran_e2_target_ip", "must be blank when E2 is disabled"))

    return errors
