#!/usr/bin/env python3

import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "bin" / "preflight-e2.py"
SPEC = importlib.util.spec_from_file_location("ota_preflight", MODULE_PATH)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


class FakeSocket:
    def __init__(self, connect_error=None):
        self.connect_error = connect_error
        self.closed = False

    def settimeout(self, timeout):
        self.timeout = timeout

    def bind(self, address):
        self.bound = address

    def connect(self, address):
        if self.connect_error:
            raise self.connect_error
        self.connected = address

    def getsockname(self):
        return (self.bound[0], 49152)

    def getpeername(self):
        return self.connected

    def close(self):
        self.closed = True


class PreflightTests(unittest.TestCase):
    @mock.patch.object(preflight.socket, "socket")
    @mock.patch.object(preflight.subprocess, "run")
    def test_success_records_payload_free_sctp_association(self, run, socket_factory):
        run.return_value = subprocess.CompletedProcess(
            [], 0, '[{"dst":"10.254.254.1","prefsrc":"192.168.1.2"}]', "")
        fake = FakeSocket()
        socket_factory.return_value = fake

        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "result.json"
            with mock.patch.object(sys, "argv", [
                    "preflight-e2.py", "--target", "10.254.254.1",
                    "--port", "32222", "--source", "192.168.1.2",
                    "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, preflight.main())
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["success"])
        self.assertFalse(result["payload_sent"])
        self.assertTrue(fake.closed)

    @mock.patch.object(preflight.socket, "socket")
    @mock.patch.object(preflight.subprocess, "run")
    def test_closed_listener_fails_and_closes_socket(self, run, socket_factory):
        run.return_value = subprocess.CompletedProcess(
            [], 0, '[{"dst":"10.254.254.1","prefsrc":"192.168.1.2"}]', "")
        fake = FakeSocket(ConnectionRefusedError("closed"))
        socket_factory.return_value = fake

        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "result.json"
            with mock.patch.object(sys, "argv", [
                    "preflight-e2.py", "--target", "10.254.254.1",
                    "--port", "32222", "--source", "192.168.1.2",
                    "--output", str(output)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(1, preflight.main())
            result = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(result["success"])
        self.assertFalse(result["payload_sent"])
        self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()
