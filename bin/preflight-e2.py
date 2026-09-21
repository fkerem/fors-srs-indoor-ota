#!/usr/bin/env python3

import argparse
import json
import socket
import subprocess
import sys


IPPROTO_SCTP = getattr(socket, "IPPROTO_SCTP", 132)


def main():
    parser = argparse.ArgumentParser(
        description="Validate the routed, payload-free SCTP path to E2Term")
    parser.add_argument("--target", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--source", required=True)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--output", default="/tmp/e2-preflight.json")
    args = parser.parse_args()

    result = {
        "target": args.target,
        "port": args.port,
        "expected_source": args.source,
        "transport": "SCTP",
        "payload_sent": False,
        "success": False,
    }
    try:
        route_proc = subprocess.run(
            ["ip", "-j", "route", "get", args.target], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        routes = json.loads(route_proc.stdout)
        if not routes:
            raise RuntimeError("no route returned")
        route = routes[0]
        result["route"] = route
        if route.get("prefsrc") != args.source:
            raise RuntimeError("route source {} does not match {}".format(
                route.get("prefsrc"), args.source))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, IPPROTO_SCTP)
        try:
            sock.settimeout(args.timeout)
            sock.bind((args.source, 0))
            sock.connect((args.target, args.port))
            result["local_socket"] = list(sock.getsockname())
            result["remote_socket"] = list(sock.getpeername())
            result["success"] = True
        finally:
            sock.close()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError,
            json.JSONDecodeError) as exc:
        result["error"] = str(exc)

    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    with open(args.output, "w", encoding="utf-8") as output:
        output.write(rendered)
    sys.stdout.write(rendered)
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
