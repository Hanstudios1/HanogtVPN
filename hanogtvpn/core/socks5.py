"""
HanogtVPN SOCKS5 Proxy Server

A local SOCKS5 proxy that tunnels traffic through the encrypted VPN
connection.  The browser or application connects to this local proxy,
which forwards data to the VPN server via the encrypted tunnel.

RFC 1928 — SOCKS Protocol Version 5
RFC 1929 — Username/Password Authentication for SOCKS V5

Usage:
    The proxy is started automatically by the ConnectionManager when
    a VPN connection is established.  It listens on 127.0.0.1:1080
    by default.
"""

import socket
import struct
import threading
import select
import time

from hanogtvpn.core.logger import VPNLogger
from hanogtvpn.core.constants import BUFFER_SIZE


# SOCKS5 constants
SOCKS_VERSION = 0x05
AUTH_NONE = 0x00
AUTH_NO_ACCEPTABLE = 0xFF
CMD_CONNECT = 0x01
CMD_BIND = 0x02
CMD_UDP_ASSOCIATE = 0x03
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03
ATYP_IPV6 = 0x04
REP_SUCCESS = 0x00
REP_GENERAL_FAILURE = 0x01
REP_NOT_ALLOWED = 0x02
REP_NETWORK_UNREACHABLE = 0x03
REP_HOST_UNREACHABLE = 0x04
REP_CONNECTION_REFUSED = 0x05
REP_TTL_EXPIRED = 0x06
REP_COMMAND_NOT_SUPPORTED = 0x07
REP_ADDRESS_NOT_SUPPORTED = 0x08


class SOCKS5Handler:
    """Handles a single SOCKS5 client connection."""

    def __init__(self, client_socket: socket.socket, client_addr: tuple):
        self.client = client_socket
        self.addr = client_addr
        self.remote: socket.socket | None = None
        self.logger = VPNLogger.get_logger("socks5")
        self.is_active = True

    def handle(self):
        """Process the SOCKS5 handshake and relay data."""
        try:
            if not self._negotiate_auth():
                return
            if not self._handle_request():
                return
            self._relay_data()
        except ConnectionResetError:
            pass
        except OSError as e:
            if self.is_active:
                self.logger.debug(f"SOCKS5 handler error for {self.addr}: {e}")
        except Exception as e:
            self.logger.error(f"SOCKS5 unexpected error: {e}")
        finally:
            self._close()

    def _negotiate_auth(self) -> bool:
        """Negotiate SOCKS5 authentication (no-auth only)."""
        try:
            # Client greeting: VER, NMETHODS, METHODS
            header = self._recv_exact(2)
            if header is None:
                return False

            version, nmethods = header[0], header[1]
            if version != SOCKS_VERSION:
                self.logger.warning(f"Invalid SOCKS version: {version}")
                return False

            methods = self._recv_exact(nmethods)
            if methods is None:
                return False

            # We only support no-authentication
            if AUTH_NONE in methods:
                self.client.sendall(struct.pack("!BB", SOCKS_VERSION, AUTH_NONE))
                return True
            else:
                self.client.sendall(
                    struct.pack("!BB", SOCKS_VERSION, AUTH_NO_ACCEPTABLE)
                )
                self.logger.warning("No acceptable auth method from client")
                return False

        except Exception as e:
            self.logger.error(f"Auth negotiation failed: {e}")
            return False

    def _handle_request(self) -> bool:
        """Handle SOCKS5 connection request."""
        try:
            # Request: VER, CMD, RSV, ATYP, DST.ADDR, DST.PORT
            header = self._recv_exact(4)
            if header is None:
                return False

            version, cmd, _, atyp = header[0], header[1], header[2], header[3]

            if version != SOCKS_VERSION:
                self._send_reply(REP_GENERAL_FAILURE, ATYP_IPV4, "0.0.0.0", 0)
                return False

            if cmd != CMD_CONNECT:
                self._send_reply(REP_COMMAND_NOT_SUPPORTED, ATYP_IPV4, "0.0.0.0", 0)
                self.logger.warning(f"Unsupported SOCKS5 command: {cmd}")
                return False

            # Parse destination address
            dst_addr, dst_port = self._parse_address(atyp)
            if dst_addr is None:
                self._send_reply(REP_ADDRESS_NOT_SUPPORTED, ATYP_IPV4, "0.0.0.0", 0)
                return False

            self.logger.debug(f"SOCKS5 CONNECT → {dst_addr}:{dst_port}")

            # Connect to the remote target
            try:
                self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.remote.settimeout(10)
                self.remote.connect((dst_addr, dst_port))
                self.remote.settimeout(None)

                bind_addr = self.remote.getsockname()
                self._send_reply(
                    REP_SUCCESS, ATYP_IPV4, bind_addr[0], bind_addr[1]
                )
                self.logger.debug(
                    f"SOCKS5 connected to {dst_addr}:{dst_port}"
                )
                return True

            except socket.timeout:
                self._send_reply(REP_TTL_EXPIRED, ATYP_IPV4, "0.0.0.0", 0)
                return False
            except ConnectionRefusedError:
                self._send_reply(
                    REP_CONNECTION_REFUSED, ATYP_IPV4, "0.0.0.0", 0
                )
                return False
            except OSError:
                self._send_reply(
                    REP_HOST_UNREACHABLE, ATYP_IPV4, "0.0.0.0", 0
                )
                return False

        except Exception as e:
            self.logger.error(f"Request handling failed: {e}")
            try:
                self._send_reply(REP_GENERAL_FAILURE, ATYP_IPV4, "0.0.0.0", 0)
            except OSError:
                pass
            return False

    def _parse_address(self, atyp: int) -> tuple:
        """Parse the destination address based on address type."""
        try:
            if atyp == ATYP_IPV4:
                raw = self._recv_exact(4)
                if raw is None:
                    return None, None
                addr = socket.inet_ntoa(raw)

            elif atyp == ATYP_DOMAIN:
                length_byte = self._recv_exact(1)
                if length_byte is None:
                    return None, None
                domain_len = length_byte[0]
                domain = self._recv_exact(domain_len)
                if domain is None:
                    return None, None
                addr = domain.decode("utf-8", errors="replace")
                # Resolve domain
                try:
                    addr = socket.gethostbyname(addr)
                except socket.gaierror:
                    self.logger.warning(f"DNS resolution failed: {addr}")
                    return None, None

            elif atyp == ATYP_IPV6:
                raw = self._recv_exact(16)
                if raw is None:
                    return None, None
                addr = socket.inet_ntop(socket.AF_INET6, raw)
            else:
                return None, None

            # Read port (2 bytes, big-endian)
            port_raw = self._recv_exact(2)
            if port_raw is None:
                return None, None
            port = struct.unpack("!H", port_raw)[0]

            return addr, port

        except Exception:
            return None, None

    def _send_reply(self, rep: int, atyp: int, bind_addr: str, bind_port: int):
        """Send SOCKS5 reply to the client."""
        try:
            addr_bytes = socket.inet_aton(bind_addr)
        except OSError:
            addr_bytes = b"\x00\x00\x00\x00"

        reply = struct.pack(
            "!BBBB", SOCKS_VERSION, rep, 0x00, ATYP_IPV4
        ) + addr_bytes + struct.pack("!H", bind_port)

        self.client.sendall(reply)

    def _relay_data(self):
        """Bidirectional data relay between client and remote using select."""
        sockets = [self.client, self.remote]

        while self.is_active:
            try:
                readable, _, exceptional = select.select(sockets, [], sockets, 30)

                if exceptional:
                    break

                for sock in readable:
                    data = sock.recv(BUFFER_SIZE)
                    if not data:
                        self.is_active = False
                        break

                    if sock is self.client:
                        self.remote.sendall(data)
                    else:
                        self.client.sendall(data)

            except (OSError, ConnectionResetError):
                break

    def _recv_exact(self, n: int) -> bytes | None:
        """Receive exactly n bytes, return None on failure."""
        data = b""
        while len(data) < n:
            try:
                chunk = self.client.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except OSError:
                return None
        return data

    def _close(self):
        """Close both sockets."""
        self.is_active = False
        for s in (self.client, self.remote):
            if s:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    s.close()
                except OSError:
                    pass


class SOCKS5Proxy:
    """Local SOCKS5 proxy server.

    Listens on a local port and forwards connections through the VPN
    tunnel (or directly for now).

    Usage::

        proxy = SOCKS5Proxy(host="127.0.0.1", port=1080)
        proxy.start()   # starts in background thread
        # ... later ...
        proxy.stop()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 1080):
        self.host = host
        self.port = port
        self.server_socket: socket.socket | None = None
        self.is_running = False
        self.logger = VPNLogger.get_logger("socks5-proxy")
        self._thread: threading.Thread | None = None
        self._handlers: list[SOCKS5Handler] = []
        self._lock = threading.Lock()

    def start(self):
        """Start the SOCKS5 proxy in a background daemon thread."""
        if self.is_running:
            return

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
        except OSError as e:
            self.logger.error(f"SOCKS5 proxy bind failed on {self.host}:{self.port}: {e}")
            return

        self.server_socket.listen(128)
        self.is_running = True

        self._thread = threading.Thread(
            target=self._accept_loop, daemon=True, name="socks5-proxy"
        )
        self._thread.start()

        self.logger.info(
            f"SOCKS5 proxy listening on {self.host}:{self.port}"
        )

    def _accept_loop(self):
        """Accept incoming SOCKS5 connections."""
        while self.is_running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()

                handler = SOCKS5Handler(client_socket, addr)
                with self._lock:
                    # Prune inactive handlers
                    self._handlers = [h for h in self._handlers if h.is_active]
                    self._handlers.append(handler)

                t = threading.Thread(
                    target=handler.handle, daemon=True,
                    name=f"socks5-{addr[0]}:{addr[1]}",
                )
                t.start()

            except socket.timeout:
                continue
            except OSError:
                if self.is_running:
                    self.logger.error("SOCKS5 proxy accept error")
                break

    def stop(self):
        """Stop the SOCKS5 proxy."""
        if not self.is_running:
            return

        self.is_running = False

        # Close all active handlers
        with self._lock:
            for handler in self._handlers:
                handler.is_active = False
                handler._close()
            self._handlers.clear()

        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        self.logger.info("SOCKS5 proxy stopped")

    @property
    def active_connections(self) -> int:
        with self._lock:
            self._handlers = [h for h in self._handlers if h.is_active]
            return len(self._handlers)
