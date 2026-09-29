#!/usr/bin/env python3

import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECK = ROOT / "bin" / "check-uhd-compat.sh"
START = ROOT / "bin" / "start-gnb.sh"
DEPLOY = ROOT / "bin" / "deploy-ocudu.sh"


class LauncherTests(unittest.TestCase):
    def run_probe(self, exit_code):
        with tempfile.TemporaryDirectory() as directory:
            workdir = pathlib.Path(directory)
            probe = workdir / "uhd_usrp_probe"
            probe.write_text(
                "#!/bin/sh\nprintf 'RFNoC compatibility check\\n'\n"
                f"exit {exit_code}\n", encoding="utf-8")
            probe.chmod(0o755)
            log = workdir / "probe.log"
            env = os.environ.copy()
            env["PATH"] = f"{workdir}{os.pathsep}{env['PATH']}"
            result = subprocess.run(
                ["bash", str(CHECK), str(log)], env=env, capture_output=True,
                text=True, check=False)
            return result, log.read_text(encoding="utf-8")

    def test_probe_success(self):
        result, log = self.run_probe(0)
        self.assertEqual(0, result.returncode)
        self.assertIn("RFNoC compatibility check", log)
        self.assertIn("probe passed", result.stdout)

    def test_probe_failure_blocks_rf(self):
        result, log = self.run_probe(42)
        self.assertEqual(1, result.returncode)
        self.assertIn("RFNoC compatibility check", log)
        self.assertIn("RF was not started", result.stderr)

    def test_launcher_requires_reservation_confirmation(self):
        result = subprocess.run(
            ["bash", str(START)], capture_output=True, text=True, check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("Refusing to start RF", result.stderr)

    def test_probe_precedes_gnb_exec(self):
        source = START.read_text(encoding="utf-8")
        self.assertLess(source.index("check-uhd-compat.sh"),
                        source.index("exec sudo"))

    def test_uhd_package_pin_and_validation_are_present(self):
        source = DEPLOY.read_text(encoding="utf-8")
        self.assertIn("UHD_PACKAGE_VERSION=4.11.0.0-0ubuntu1~jammy4", source)
        self.assertIn('libuhd-dev="$UHD_PACKAGE_VERSION"', source)
        self.assertIn('uhd-host="$UHD_PACKAGE_VERSION"', source)
        self.assertIn('"$UHD_HOST_PACKAGE_VERSION" == "$UHD_PACKAGE_VERSION"', source)
        self.assertIn('"$UHD_DEV_PACKAGE_VERSION" == "$UHD_PACKAGE_VERSION"', source)


if __name__ == "__main__":
    unittest.main()
