#!/usr/bin/env python3

import re


VLAN_NAME_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9-]{0,30}\Z")
COMMIT_RE = re.compile(r"\A[0-9a-f]{40}\Z")
AGENT_MODES = {"du-only", "all"}


try:
    _TEXT_TYPE = unicode
except NameError:
    _TEXT_TYPE = str


def _parameter_text(value):
    """Normalize portal strings for both old Python 2 and Python 3 runtimes."""
    if value is None:
        return ""
    if _TEXT_TYPE is not str and isinstance(value, _TEXT_TYPE):
        return value.encode("ascii")
    if _TEXT_TYPE is str and isinstance(value, bytes):
        return value.decode("ascii")
    if isinstance(value, _TEXT_TYPE):
        return value
    return str(value)


def _parse_ipv4(value):
    """Return an IPv4 address as an integer, or None when invalid."""
    text = _parameter_text(value)
    parts = text.split(".")
    if len(parts) != 4:
        return None
    octets = []
    for part in parts:
        if not part or not part.isdigit():
            return None
        octet = int(part, 10)
        if octet > 255:
            return None
        octets.append(octet)
    return ((octets[0] << 24) | (octets[1] << 16) |
            (octets[2] << 8) | octets[3])


def _valid_netmask(mask):
    """Return the mask integer when contiguous, or None when invalid."""
    mask_value = _parse_ipv4(mask)
    if mask_value is None:
        return None
    inverse = (~mask_value) & 0xffffffff
    if inverse & (inverse + 1):
        return None
    return mask_value


def _network(peer_ip, netmask):
    peer = _parse_ipv4(peer_ip)
    mask = _valid_netmask(netmask)
    if peer is None or mask is None:
        return None
    inverse = (~mask) & 0xffffffff
    return peer & mask, peer | inverse


def _format_ipv4(value):
    return "{}.{}.{}.{}".format(
        (value >> 24) & 255, (value >> 16) & 255,
        (value >> 8) & 255, value & 255)


def _prefix_length(mask):
    prefix = 0
    bit = 0x80000000
    while bit and mask & bit:
        prefix += 1
        bit >>= 1
    return prefix


def shared_network_cidr(peer_ip, netmask):
    network = _network(peer_ip, netmask)
    mask = _valid_netmask(netmask)
    if network is None or mask is None:
        return ""
    return "{}/{}".format(_format_ipv4(network[0]), _prefix_length(mask))


def validate_parameters(enable_e2, vlan_name, peer_ip, netmask, target_ip,
                        port, agent_mode, ocudu_commit, approved_commit):
    errors = []

    vlan_text = _parameter_text(vlan_name)
    peer_text = _parameter_text(peer_ip)
    netmask_text = _parameter_text(netmask)
    target_text = _parameter_text(target_ip)
    agent_text = _parameter_text(agent_mode)
    commit_text = _parameter_text(ocudu_commit)
    approved_text = _parameter_text(approved_commit)

    if agent_text not in AGENT_MODES:
        errors.append(("oran_e2_agent_mode", "must be du-only or all"))

    if not COMMIT_RE.match(commit_text):
        errors.append(("ocudu_commit_hash", "must be a full lowercase 40-character commit hash"))
    elif commit_text != approved_text:
        errors.append(("ocudu_commit_hash", "must match the approved release_26_04 commit"))

    try:
        port_value = int(port)
        if not 20000 <= port_value <= 40000:
            raise ValueError
    except (TypeError, ValueError):
        errors.append(("oran_e2_port", "must be an integer from 20000 through 40000"))

    peer = _parse_ipv4(peer_text)
    if peer is None:
        peer = None
        errors.append(("oran_shared_vlan_ip", "must be a valid IPv4 address"))

    network = _network(peer_text, netmask_text)
    if network is None:
        network = None
        errors.append(("oran_shared_vlan_netmask", "must form a valid IPv4 network with the peer address"))

    target = None
    if target_text:
        target = _parse_ipv4(target_text)
        if target is None:
            errors.append(("oran_e2_target_ip", "must be a valid IPv4 address"))

    if enable_e2:
        if not VLAN_NAME_RE.match(vlan_text):
            errors.append(("oran_shared_vlan_name", "must contain 1-31 letters, digits, or hyphens and start with a letter or digit when E2 is enabled"))
        if not target_text:
            errors.append(("oran_e2_target_ip", "is required when E2 is enabled"))
        if peer is not None and network is not None and peer in (
                network[0], network[1]):
            errors.append(("oran_shared_vlan_ip", "must be a usable host address"))
        if target is not None and network is not None:
            if not network[0] <= target <= network[1]:
                errors.append(("oran_e2_target_ip", "must be in the shared-VLAN subnet"))
            elif target in (network[0], network[1]):
                errors.append(("oran_e2_target_ip", "must be a usable host address"))
        if peer is not None and target is not None and peer == target:
            errors.append(("oran_e2_target_ip", "must differ from the peer shared-VLAN address"))
    else:
        if vlan_text:
            errors.append(("oran_shared_vlan_name", "must be blank when E2 is disabled"))
        if target_text:
            errors.append(("oran_e2_target_ip", "must be blank when E2 is disabled"))

    return errors
