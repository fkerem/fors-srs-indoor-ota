#!/usr/bin/env python3

import pathlib
import sys
import unittest


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from profile_validation import shared_network_cidr, validate_parameters  # noqa: E402


APPROVED = "050a2bb72e1d794cd60570d809987c1fcda3e54b"


class ProfileValidationTests(unittest.TestCase):
    def test_standalone_defaults(self):
        self.assertEqual([], validate_parameters(
            False, "", "10.254.254.2", "255.255.255.0", "", 32222,
            "du-only", APPROVED, APPROVED))

    def test_valid_du_e2(self):
        self.assertEqual([], validate_parameters(
            True, "oran-vlan-stage2", "10.254.254.2", "255.255.255.0",
            "10.254.254.1", 32222, "du-only", APPROVED, APPROVED))
        self.assertEqual("10.254.254.0/24", shared_network_cidr(
            "10.254.254.2", "255.255.255.0"))

    def test_disabled_e2_rejects_e2_addresses(self):
        errors = validate_parameters(
            False, "phase2", "10.254.254.2", "255.255.255.0",
            "10.254.254.1", 32222, "all", APPROVED, APPROVED)
        self.assertEqual(
            {"oran_shared_vlan_name", "oran_e2_target_ip"},
            {field for field, _ in errors})

    def test_wrong_commit_and_network_are_rejected(self):
        errors = validate_parameters(
            True, "bad_name", "10.254.254.2", "255.255.255.0",
            "10.0.0.1", 70000, "invalid", "a" * 40, APPROVED)
        fields = {field for field, _ in errors}
        self.assertTrue({
            "oran_shared_vlan_name", "oran_e2_target_ip", "oran_e2_port",
            "oran_e2_agent_mode", "ocudu_commit_hash"}.issubset(fields))

    def test_portal_encoded_values_are_accepted(self):
        self.assertEqual([], validate_parameters(
            True, b"oran-vlan-stage2", b"10.254.254.2",
            b"255.255.255.0", b"10.254.254.1", 32222,
            b"du-only", APPROVED, APPROVED))

    def test_ocudu_e2_port_range_is_enforced(self):
        for port in (19999, 40001):
            with self.subTest(port=port):
                errors = validate_parameters(
                    True, "phase2", "10.254.254.2", "255.255.255.0",
                    "10.254.254.1", port, "du-only", APPROVED, APPROVED)
                self.assertIn("oran_e2_port", {field for field, _ in errors})


if __name__ == "__main__":
    unittest.main()
