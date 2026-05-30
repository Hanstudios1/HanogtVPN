"""
Tests for the SOCKS5 proxy module.
"""

import socket
import struct
import threading
import time
import unittest

from hanogtvpn.core.socks5 import SOCKS5Proxy, SOCKS_VERSION, AUTH_NONE


class TestSOCKS5Proxy(unittest.TestCase):
    """Test SOCKS5 proxy startup, shutdown, and basic negotiation."""

    def test_start_and_stop(self):
        proxy = SOCKS5Proxy(host="127.0.0.1", port=18080)
        proxy.start()
        self.assertTrue(proxy.is_running)
        time.sleep(0.2)

        # Should be able to connect
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 18080))
        s.close()

        proxy.stop()
        self.assertFalse(proxy.is_running)

    def test_auth_negotiation(self):
        proxy = SOCKS5Proxy(host="127.0.0.1", port=18081)
        proxy.start()
        time.sleep(0.2)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 18081))

            # Send greeting: version 5, 1 method (no-auth)
            s.sendall(struct.pack("!BBB", SOCKS_VERSION, 1, AUTH_NONE))

            # Expect response: version 5, method 0 (no-auth)
            response = s.recv(2)
            self.assertEqual(len(response), 2)
            self.assertEqual(response[0], SOCKS_VERSION)
            self.assertEqual(response[1], AUTH_NONE)

            s.close()
        finally:
            proxy.stop()

    def test_active_connections_count(self):
        proxy = SOCKS5Proxy(host="127.0.0.1", port=18082)
        proxy.start()
        time.sleep(0.2)

        self.assertEqual(proxy.active_connections, 0)
        proxy.stop()

    def test_double_start(self):
        proxy = SOCKS5Proxy(host="127.0.0.1", port=18083)
        proxy.start()
        proxy.start()  # Should be a no-op
        self.assertTrue(proxy.is_running)
        proxy.stop()

    def test_double_stop(self):
        proxy = SOCKS5Proxy(host="127.0.0.1", port=18084)
        proxy.start()
        proxy.stop()
        proxy.stop()  # Should be a no-op
        self.assertFalse(proxy.is_running)


if __name__ == "__main__":
    unittest.main()
