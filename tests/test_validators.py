"""
Tests for input validators.
"""

import unittest

from hanogtvpn.utils.validators import (
    validate_ip,
    validate_port,
    validate_hostname,
    sanitize_input,
)


class TestValidateIP(unittest.TestCase):

    def test_valid_ips(self):
        valid = ["127.0.0.1", "0.0.0.0", "192.168.1.1", "255.255.255.255", "10.0.0.1"]
        for ip in valid:
            with self.subTest(ip=ip):
                self.assertTrue(validate_ip(ip))

    def test_invalid_ips(self):
        invalid = [
            "", "abc", "256.1.1.1", "1.2.3", "1.2.3.4.5",
            "192.168.1.999", "-1.0.0.0", "hello.world",
        ]
        for ip in invalid:
            with self.subTest(ip=ip):
                self.assertFalse(validate_ip(ip))

    def test_whitespace_stripped(self):
        self.assertTrue(validate_ip("  10.0.0.1  "))


class TestValidatePort(unittest.TestCase):

    def test_valid_ports(self):
        for port in [1, 80, 443, 8080, 9999, 65535]:
            with self.subTest(port=port):
                self.assertTrue(validate_port(port))

    def test_valid_ports_as_strings(self):
        for port in ["1", "443", "9999", "65535"]:
            with self.subTest(port=port):
                self.assertTrue(validate_port(port))

    def test_invalid_ports(self):
        for port in [0, -1, 65536, 100000, "abc", "", None, "0"]:
            with self.subTest(port=port):
                self.assertFalse(validate_port(port))


class TestValidateHostname(unittest.TestCase):

    def test_valid_hostnames(self):
        valid = [
            "example.com", "sub.domain.org", "my-server",
            "vpn1.hanogtvpn.com", "localhost",
        ]
        for h in valid:
            with self.subTest(hostname=h):
                self.assertTrue(validate_hostname(h))

    def test_invalid_hostnames(self):
        invalid = [
            "", "-start.com", "end-.com",
            "a" * 254,  # Too long
        ]
        for h in invalid:
            with self.subTest(hostname=h):
                self.assertFalse(validate_hostname(h))


class TestSanitizeInput(unittest.TestCase):

    def test_removes_null_bytes(self):
        self.assertEqual(sanitize_input("hello\x00world"), "helloworld")

    def test_removes_control_chars(self):
        self.assertEqual(sanitize_input("test\x01\x02data"), "testdata")

    def test_strips_whitespace(self):
        self.assertEqual(sanitize_input("  hello  "), "hello")

    def test_preserves_normal_text(self):
        self.assertEqual(sanitize_input("normal input"), "normal input")

    def test_handles_non_string(self):
        self.assertEqual(sanitize_input(123), "")
        self.assertEqual(sanitize_input(None), "")


if __name__ == "__main__":
    unittest.main()
