#!/usr/bin/env python3

import os

import geni.portal as portal
import geni.rspec.igext as IG
import geni.rspec.pg as rspec
import geni.rspec.emulab.spectrum as spectrum

from profile_validation import shared_network_cidr, validate_parameters


tourDescription = """
### OCUDU 5G using the POWDER Indoor OTA Lab

This profile deploys an Open5GS core, an OCUDU gNodeB connected to an X310,
and up to four COTS UE nodes. It can run standalone or connect the gNodeB to an
O-RAN SC Near-RT RIC through a private cross-experiment shared VLAN.

The profile reserves spectrum but never starts the gNodeB automatically. An
approved spectrum reservation and an explicit launcher confirmation are
required before RF transmission.
"""

tourInstructions = """
Wait until every startup service is `Finished` before proceeding.

The Open5GS services run on `cn5g`. Inspect them with:

```
systemctl status open5gs-*
```

On the selected `ota-x310-*-gnuradio-comp` node, review the exact OCUDU source
and build record:

```
cat /var/tmp/ocudu-build-provenance.txt
```

If E2 is enabled, the launcher first verifies route selection and establishes
and closes an SCTP association without sending E2AP payloads. It refuses to
start without an explicit RF-reservation acknowledgement:

```
/local/repository/bin/start-gnb.sh --confirm-rf-reservation
```

The same command starts standalone OCUDU when E2 is disabled. Nothing in the
profile automatically transmits RF.

After the gNodeB is running, start the Quectel connection manager on a selected
`ota-nuc*-cots-ue` node:

```
sudo quectel-CM -s internet -4
```

Then enable the modem in another session:

```
sudo sh -c "chat -t 1 -sv '' AT OK 'AT+CFUN=1' OK < /dev/ttyUSB2 > /dev/ttyUSB2"
```
"""

BIN_PATH = "/local/repository/bin"
UBUNTU_IMG = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD"
COTS_UE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:cots-jammy-image"
COMP_MANAGER_ID = "urn:publicid:IDN+emulab.net+authority+cm"
APPROVED_OCUDU_COMMIT = "050a2bb72e1d794cd60570d809987c1fcda3e54b"
OPEN5GS_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-open5gs.sh")
OCUDU_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-ocudu.sh")
CN_FORWARD_SCRIPT = os.path.join(BIN_PATH, "setup-cn-forwarding.sh")
GNB_ROUTE_SCRIPT = os.path.join(BIN_PATH, "setup-gnb-route.sh")
ORAN_SHARED_VLAN_IP_DEFAULT = "10.254.254.2"
ORAN_SHARED_VLAN_NETMASK_DEFAULT = "255.255.255.0"

pc = portal.Context()

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
    ("d760p", "Emulab, d760"),
    ("d760-gpu", "Emulab, d760 with L40S GPU"),
]
pc.defineParameter(
    "sdr_nodetype", "Type of compute node paired with the SDR",
    portal.ParameterType.STRING, node_types[1], node_types)
pc.defineParameter(
    "cn_nodetype", "Type of compute node for the 5G core",
    portal.ParameterType.STRING, node_types[0], node_types)
pc.defineParameter(
    "sdr_compute_image", "Image for compute connected to the SDR",
    portal.ParameterType.STRING, "", advanced=True)
pc.defineParameter(
    "ocudu_commit_hash", "Approved OCUDU commit",
    portal.ParameterType.STRING, APPROVED_OCUDU_COMMIT,
    longDescription="Pinned release_26_04 commit; alternate revisions are rejected.",
    advanced=True)
pc.defineParameter(
    "enable_oran_e2", "Enable O-RAN E2 over a private shared VLAN",
    portal.ParameterType.BOOLEAN, False)
pc.defineParameter(
    "oran_e2_agent_mode", "OCUDU E2 agents",
    portal.ParameterType.STRING, "du-only",
    [("du-only", "DU only"), ("all", "DU, CU-CP, and CU-UP")],
    advanced=True)
pc.defineParameter(
    "oran_shared_vlan_name", "Existing private shared VLAN name",
    portal.ParameterType.STRING, "",
    longDescription="Required only for E2. Use a fresh random letters/digits/hyphens name.",
    advanced=True)
pc.defineParameter(
    "oran_shared_vlan_ip", "Peer shared-VLAN address",
    portal.ParameterType.STRING, ORAN_SHARED_VLAN_IP_DEFAULT, advanced=True)
pc.defineParameter(
    "oran_shared_vlan_netmask", "Shared-VLAN netmask",
    portal.ParameterType.STRING, ORAN_SHARED_VLAN_NETMASK_DEFAULT, advanced=True)
pc.defineParameter(
    "oran_e2_target_ip", "RIC owner shared-VLAN address",
    portal.ParameterType.STRING, "", advanced=True)
pc.defineParameter(
    "oran_e2_port", "E2Term SCTP NodePort",
    portal.ParameterType.INTEGER, 32222, advanced=True)

indoor_ota_x310s = [
    ("ota-x310-1", "USRP X310 #1"),
    ("ota-x310-2", "USRP X310 #2"),
    ("ota-x310-3", "USRP X310 #3"),
    ("ota-x310-4", "USRP X310 #4"),
]
pc.defineParameter(
    "x310_radio", "X310 radio for the gNodeB",
    portal.ParameterType.STRING, indoor_ota_x310s[0], indoor_ota_x310s)

indoor_ota_nucs = [
    ("ota-nuc{}".format(i), "Indoor OTA NUC {}".format(i))
    for i in range(1, 5)
]
pc.defineStructParameter(
    "ue_nodes", "Indoor OTA NUC with COTS UE",
    [{"node_id": "ota-nuc1"}], multiValue=True, min=1, max=4,
    members=[portal.Parameter(
        "node_id", "Indoor OTA NUC", portal.ParameterType.STRING,
        indoor_ota_nucs[0], indoor_ota_nucs)])
pc.defineStructParameter(
    "freq_ranges", "Frequency ranges to transmit in",
    [{"freq_min": 3410.0, "freq_max": 3450.0}], multiValue=True, min=0,
    multiValueTitle="Frequency ranges to be used for transmission.",
    members=[
        portal.Parameter(
            "freq_min", "Frequency range minimum",
            portal.ParameterType.BANDWIDTH, 3410.0),
        portal.Parameter(
            "freq_max", "Frequency range maximum",
            portal.ParameterType.BANDWIDTH, 3450.0),
    ])

params = pc.bindParameters()
for field, message in validate_parameters(
        params.enable_oran_e2, params.oran_shared_vlan_name,
        params.oran_shared_vlan_ip, params.oran_shared_vlan_netmask,
        params.oran_e2_target_ip, params.oran_e2_port,
        params.oran_e2_agent_mode, params.ocudu_commit_hash,
        APPROVED_OCUDU_COMMIT):
    pc.reportError(portal.ParameterError(message, [field]))
pc.verifyParameters()

shared_cidr = shared_network_cidr(
    params.oran_shared_vlan_ip, params.oran_shared_vlan_netmask)
request = pc.makeRequestRSpec()

cn_node = request.RawPC("cn5g")
cn_node.component_manager_id = COMP_MANAGER_ID
cn_node.hardware_type = params.cn_nodetype
cn_node.disk_image = UBUNTU_IMG
cn_if = cn_node.addInterface("cn-if")
cn_if.addAddress(rspec.IPv4Address("192.168.1.1", "255.255.255.0"))
cn_link = request.Link("cn-link")
cn_link.setNoBandwidthShaping()
cn_link.addInterface(cn_if)
cn_node.addService(rspec.Execute(shell="bash", command=OPEN5GS_DEPLOY_SCRIPT))

if params.enable_oran_e2:
    oran_if = cn_node.addInterface("oran-shared-if")
    oran_if.addAddress(rspec.IPv4Address(
        params.oran_shared_vlan_ip, params.oran_shared_vlan_netmask))
    oran_link = request.Link("oran-shared-vlan")
    oran_link.addInterface(oran_if)
    oran_link.connectSharedVlan(params.oran_shared_vlan_name)

    forward_cmd = "{} '{}' '{}' '{}'".format(
        CN_FORWARD_SCRIPT, params.oran_shared_vlan_ip,
        "192.168.1.1", shared_cidr)
    cn_node.addService(rspec.Execute(shell="bash", command=forward_cmd))


def add_x310_pair(idx, x310_radio):
    node = request.RawPC("{}-gnuradio-comp".format(x310_radio))
    node.component_manager_id = COMP_MANAGER_ID
    node.hardware_type = params.sdr_nodetype
    node.disk_image = params.sdr_compute_image or UBUNTU_IMG

    radio_if = node.addInterface("usrp-if")
    radio_if.addAddress(rspec.IPv4Address("192.168.40.1", "255.255.255.0"))
    radio_link = request.Link("radio-link-{}".format(idx))
    radio_link.addInterface(radio_if)
    radio = request.RawPC("{}-gnb-sdr".format(x310_radio))
    radio.component_id = x310_radio
    radio.component_manager_id = COMP_MANAGER_ID
    radio_link.addNode(radio)

    lan_ip = "192.168.1.{}".format(idx + 2)
    nodeb_cn_if = node.addInterface("nodeb-cn-if")
    nodeb_cn_if.addAddress(rspec.IPv4Address(lan_ip, "255.255.255.0"))
    cn_link.addInterface(nodeb_cn_if)

    enabled = "1" if params.enable_oran_e2 else "0"
    deploy_cmd = "{} '{}' '{}' '{}' '{}' '{}'".format(
        OCUDU_DEPLOY_SCRIPT, params.ocudu_commit_hash, enabled,
        params.oran_e2_target_ip, params.oran_e2_port,
        params.oran_e2_agent_mode)
    node.addService(rspec.Execute(shell="bash", command=deploy_cmd))
    node.addService(rspec.Execute(
        shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))
    if params.enable_oran_e2:
        route_cmd = "{} '{}' '{}' '{}'".format(
            GNB_ROUTE_SCRIPT, lan_ip, shared_cidr, "192.168.1.1")
        node.addService(rspec.Execute(shell="bash", command=route_cmd))


def add_cots_ue(b210_node):
    node = request.RawPC("{}-cots-ue".format(b210_node))
    node.component_manager_id = COMP_MANAGER_ID
    node.component_id = b210_node
    node.disk_image = COTS_UE_IMG
    node.addService(rspec.Execute(
        shell="bash", command="/local/repository/bin/module-off.sh"))
    node.addService(rspec.Execute(
        shell="bash", command="/local/repository/bin/update-udhcpc-script.sh"))
    node.addService(rspec.Execute(
        shell="bash", command="sudo apt-get update && sudo apt-get install -y iperf3"))


add_x310_pair(0, params.x310_radio)
for ue_node in params.ue_nodes:
    add_cots_ue(ue_node.node_id)
for freq_range in params.freq_ranges:
    request.requestSpectrum(freq_range.freq_min, freq_range.freq_max, 0)

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.MARKDOWN, tourInstructions)
request.addTour(tour)
pc.printRequestRSpec(request)
