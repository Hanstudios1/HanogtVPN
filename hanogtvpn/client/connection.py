"""
HanogtVPN Connection Manager

Background-threaded connection lifecycle: handshake, data tunnel,
heartbeat, statistics, and auto-reconnect.  All GUI callbacks are
dispatched via ``root.after()`` for thread safety.
"""

import socket
import threading
import time
from typing import Callable, Optional, List

from hanogtvpn.core.constants import (
    ConnectionState,
    PacketType,
    HEARTBEAT_INTERVAL,
    CONNECTION_TIMEOUT,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_DELAY,
)
from hanogtvpn.core.crypto import CryptoEngine
from hanogtvpn.core.protocol import VPNProtocol
from hanogtvpn.core.logger import VPNLogger
from hanogtvpn.core.socks5 import SOCKS5Proxy

SOCKS5_PORT = 1080


class ConnectionManager:
    """Manages the VPN connection lifecycle in background threads.

    All registered callbacks are invoked on the Tk main thread via
    ``root.after()``, so the GUI never needs locks.
    """

    def __init__(self, root_window=None):
        self.root = root_window  # Tk root — for after() dispatch
        self.state = ConnectionState.DISCONNECTED
        self.crypto = CryptoEngine()
        self.session_key: Optional[bytes] = None
        self.sock: Optional[socket.socket] = None
        self.logger = VPNLogger.get_logger("connection")

        # Stats
        self.bytes_sent = 0
        self.bytes_received = 0
        self.connected_since: Optional[float] = None
        self._prev_bytes_sent = 0
        self._prev_bytes_received = 0
        self.upload_speed = 0.0
        self.download_speed = 0.0
        self.current_ping = -1.0

        # Callbacks
        self._state_callbacks: List[Callable] = []
        self._stats_callbacks: List[Callable] = []

        # Threading
        self._lock = threading.Lock()
        self._connect_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stats_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None

        # Connection target
        self._host = ""
        self._port = 0

        # SOCKS5 proxy
        self.socks5_proxy: SOCKS5Proxy | None = None

    # === Callback registration ========================================

    def add_state_callback(self, cb: Callable):
        self._state_callbacks.append(cb)

    def add_stats_callback(self, cb: Callable):
        self._stats_callbacks.append(cb)

    # === Public API ====================================================

    def connect(self, host: str, port: int):
        """Start connection in a background thread."""
        if self.state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
            return
        self._host = host
        self._port = port
        self._connect_thread = threading.Thread(
            target=self._connect_worker, daemon=True
        )
        self._connect_thread.start()

    def disconnect(self):
        """Graceful disconnect."""
        if self.state == ConnectionState.DISCONNECTED:
            return
        self._set_state(ConnectionState.DISCONNECTING)

        # Send disconnect packet (best-effort)
        if self.sock:
            try:
                pkt = VPNProtocol.create_disconnect()
                self.sock.sendall(pkt)
            except OSError:
                pass

        self._cleanup()
        self._set_state(ConnectionState.DISCONNECTED)
        self.logger.info("Disconnected")

    def get_stats(self) -> dict:
        duration = 0.0
        if self.connected_since:
            duration = time.time() - self.connected_since
        return {
            "state": self.state,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "upload_speed": self.upload_speed,
            "download_speed": self.download_speed,
            "duration": duration,
            "ping": self.current_ping,
        }

    # === Internal workers =============================================

    def _connect_worker(self):
        """Background connection thread."""
        self._set_state(ConnectionState.CONNECTING)
        self.bytes_sent = 0
        self.bytes_received = 0
        self._prev_bytes_sent = 0
        self._prev_bytes_received = 0
        self.upload_speed = 0.0
        self.download_speed = 0.0

        try:
            # 1. Create socket and connect
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(CONNECTION_TIMEOUT)
            self.logger.info(f"Connecting to {self._host}:{self._port}...")

            start = time.perf_counter()
            self.sock.connect((self._host, self._port))
            self.current_ping = round((time.perf_counter() - start) * 1000, 1)

            # 2. ECDH Handshake
            if not self._perform_handshake():
                raise ConnectionError("Handshake failed")

            # 3. Connected!
            self.sock.settimeout(HEARTBEAT_INTERVAL * 3)
            self.connected_since = time.time()
            self._set_state(ConnectionState.CONNECTED)
            self.logger.info(
                f"Connected to {self._host}:{self._port} "
                f"(ping={self.current_ping}ms)"
            )

            # 3b. Start SOCKS5 proxy
            self.socks5_proxy = SOCKS5Proxy(host="127.0.0.1", port=SOCKS5_PORT)
            self.socks5_proxy.start()
            self.logger.info(f"SOCKS5 proxy started on 127.0.0.1:{SOCKS5_PORT}")

            # 4. Start background loops
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True
            )
            self._heartbeat_thread.start()

            self._stats_thread = threading.Thread(
                target=self._stats_loop, daemon=True
            )
            self._stats_thread.start()

            self._receive_loop()

        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self._cleanup()
            self._set_state(ConnectionState.ERROR)

    def _perform_handshake(self) -> bool:
        """Client-side ECDH + RSA handshake."""
        try:
            # Generate client ECDH keypair
            client_pub_bytes, client_priv_key = self.crypto.generate_ecdh_keypair()

            # Send HANDSHAKE_REQUEST
            request = VPNProtocol.create_handshake_request(client_pub_bytes)
            self.sock.sendall(request)
            self.logger.debug("Sent HANDSHAKE_REQUEST")

            # Receive HANDSHAKE_RESPONSE
            pkt_type, payload = VPNProtocol.recv_packet(self.sock)
            if pkt_type != PacketType.HANDSHAKE_RESPONSE:
                self.logger.error(f"Expected HANDSHAKE_RESPONSE, got {pkt_type}")
                return False

            # Parse response
            resp = VPNProtocol.parse_handshake_response(payload)
            server_ecdh_pub = resp["ecdh_public_key"]
            rsa_signature = resp["rsa_signature"]
            server_rsa_pem = resp["server_public_key_pem"]

            # Verify RSA signature
            server_rsa_key = self.crypto.deserialize_public_key(server_rsa_pem)
            if not self.crypto.verify_signature(
                server_rsa_key, rsa_signature, server_ecdh_pub
            ):
                self.logger.error("RSA signature verification failed!")
                return False

            # Derive session key
            self.session_key = self.crypto.derive_shared_secret(
                client_priv_key, server_ecdh_pub
            )
            self.logger.info("Handshake completed — session key derived")
            return True

        except Exception as e:
            self.logger.error(f"Handshake error: {e}")
            return False

    def _receive_loop(self):
        """Receive packets from the server."""
        while self.state == ConnectionState.CONNECTED:
            try:
                pkt_type, payload = VPNProtocol.recv_packet(
                    self.sock, self.crypto, self.session_key
                )

                if pkt_type is None:
                    self.logger.info("Server closed connection")
                    break

                if pkt_type == PacketType.DATA:
                    with self._lock:
                        self.bytes_received += len(payload)

                elif pkt_type == PacketType.HEARTBEAT:
                    pass  # Heartbeat ack received

                elif pkt_type == PacketType.DISCONNECT:
                    self.logger.info("Server requested disconnect")
                    break

                elif pkt_type == PacketType.ERROR:
                    msg = payload.decode("utf-8", errors="replace")
                    self.logger.error(f"Server error: {msg}")
                    break

            except socket.timeout:
                continue
            except ConnectionError:
                self.logger.warning("Connection lost")
                break
            except OSError:
                if self.state == ConnectionState.CONNECTED:
                    self.logger.warning("Socket error in receive loop")
                break
            except Exception as e:
                self.logger.error(f"Receive error: {e}")
                break

        # Connection ended
        if self.state == ConnectionState.CONNECTED:
            self._cleanup()
            self._set_state(ConnectionState.DISCONNECTED)

    def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self.state == ConnectionState.CONNECTED:
            try:
                time.sleep(HEARTBEAT_INTERVAL)
                if self.state != ConnectionState.CONNECTED or not self.sock:
                    break
                pkt = VPNProtocol.create_heartbeat()
                self.sock.sendall(pkt)
            except OSError:
                break
            except Exception:
                break

    def _stats_loop(self):
        """Update speed statistics every second."""
        while self.state == ConnectionState.CONNECTED:
            try:
                time.sleep(1.0)
                if self.state != ConnectionState.CONNECTED:
                    break

                with self._lock:
                    self.upload_speed = self.bytes_sent - self._prev_bytes_sent
                    self.download_speed = self.bytes_received - self._prev_bytes_received
                    self._prev_bytes_sent = self.bytes_sent
                    self._prev_bytes_received = self.bytes_received

                self._notify_stats()
            except Exception:
                break

    # === State management =============================================

    def _set_state(self, new_state: ConnectionState):
        self.state = new_state
        self._notify_state()

    def _notify_state(self):
        for cb in self._state_callbacks:
            if self.root:
                self.root.after(0, lambda c=cb: c(self.state))
            else:
                try:
                    cb(self.state)
                except Exception:
                    pass

    def _notify_stats(self):
        stats = self.get_stats()
        for cb in self._stats_callbacks:
            if self.root:
                self.root.after(0, lambda c=cb, s=stats: c(s))
            else:
                try:
                    cb(stats)
                except Exception:
                    pass

    def _cleanup(self):
        # Stop SOCKS5 proxy
        if self.socks5_proxy:
            self.socks5_proxy.stop()
            self.socks5_proxy = None

        self.session_key = None
        self.connected_since = None
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
