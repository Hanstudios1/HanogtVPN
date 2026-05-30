"""
HanogtVPN Server

Accepts and manages client connections, delegates each to a
``ClientHandler`` running inside a bounded thread pool, and
provides graceful startup / shutdown with signal handling.
"""

import argparse
import os
import signal
import socket
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from hanogtvpn.core.constants import DEFAULT_PORT, ConnectionState
from hanogtvpn.core.crypto import CryptoEngine
from hanogtvpn.core.logger import VPNLogger
from hanogtvpn.server.handler import ClientHandler


class VPNServer:
    """HanogtVPN Server — accepts and manages client connections.

    Usage::

        server = VPNServer(host="0.0.0.0", port=9999)
        server.start()           # blocks until shutdown signal
        # or call server.stop()  # from another thread

    Attributes:
        host:         Bind address (default ``0.0.0.0``).
        port:         Bind port (default ``DEFAULT_PORT``).
        max_clients:  Maximum simultaneous clients.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = DEFAULT_PORT,
        max_clients: int = 50,
    ):
        self.host = host
        self.port = port
        self.max_clients = max_clients

        self.server_socket: socket.socket | None = None
        self.is_running = False
        self.clients: list[ClientHandler] = []
        self.crypto = CryptoEngine()
        self.logger = VPNLogger.get_logger("server")
        self.thread_pool = ThreadPoolExecutor(
            max_workers=max_clients,
            thread_name_prefix="vpn-client",
        )
        self._lock = threading.Lock()
        self._started_at: float | None = None

        # RSA keys for server identity
        self.rsa_private_key = None
        self.rsa_public_key = None

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _load_or_generate_keys(self):
        """Load RSA keys from the ``keys/`` directory next to the project
        root, or generate and persist a new keypair if none exist.
        """
        keys_dir = os.path.join(
            os.path.dirname(  # hanogtvpn/
                os.path.dirname(  # hanogtvpn/server/
                    os.path.abspath(__file__)
                )
            ),
            os.pardir,
            "keys",
        )
        keys_dir = os.path.normpath(keys_dir)
        os.makedirs(keys_dir, exist_ok=True)

        try:
            self.rsa_private_key, self.rsa_public_key = self.crypto.load_rsa_keys(
                keys_dir
            )
            self.logger.info(f"RSA keys loaded from {keys_dir}")
        except Exception:
            self.logger.info("No existing RSA keys found — generating new keypair")
            self.rsa_private_key, self.rsa_public_key = (
                self.crypto.generate_rsa_keypair()
            )
            self.crypto.save_rsa_keys(
                self.rsa_private_key, self.rsa_public_key, keys_dir
            )
            self.logger.info(f"New RSA keys generated and saved to {keys_dir}")

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the VPN server (blocking).

        Sets up the listening socket, registers OS signal handlers, and
        enters the accept loop.  Call :py:meth:`stop` from another thread
        or send ``SIGINT`` / ``SIGTERM`` to shut down gracefully.
        """
        self._load_or_generate_keys()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
        except OSError as e:
            self.logger.error(f"Failed to bind to {self.host}:{self.port} — {e}")
            sys.exit(1)

        self.server_socket.listen(self.max_clients)
        self.is_running = True
        self._started_at = time.time()

        self.logger.info(
            f"╔══════════════════════════════════════════════╗"
        )
        self.logger.info(
            f"║   HanogtVPN Server listening on              ║"
        )
        self.logger.info(
            f"║   {self.host}:{self.port:<39}║"
        )
        self.logger.info(
            f"║   Max clients: {self.max_clients:<30}║"
        )
        self.logger.info(
            f"╚══════════════════════════════════════════════╝"
        )

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._accept_loop()

    def _accept_loop(self):
        """Accept incoming client connections until shutdown."""
        while self.is_running:
            try:
                # Short timeout so we can re-check ``is_running`` periodically
                self.server_socket.settimeout(1.0)
                client_socket, addr = self.server_socket.accept()

                # Enforce the maximum client limit
                with self._lock:
                    # Prune handlers that are no longer active
                    self.clients = [c for c in self.clients if c.is_active]

                    if len(self.clients) >= self.max_clients:
                        self.logger.warning(
                            f"Max clients ({self.max_clients}) reached — "
                            f"rejecting {addr[0]}:{addr[1]}"
                        )
                        try:
                            client_socket.close()
                        except OSError:
                            pass
                        continue

                self.logger.info(f"New connection from {addr[0]}:{addr[1]}")

                handler = ClientHandler(
                    client_socket,
                    addr,
                    self.rsa_private_key,
                    self.rsa_public_key,
                    self.crypto,
                )

                with self._lock:
                    self.clients.append(handler)

                self.thread_pool.submit(handler.handle)

            except socket.timeout:
                # Normal — just loop back and re-check is_running
                continue

            except OSError:
                # Socket was closed (e.g. during shutdown)
                if self.is_running:
                    self.logger.error("Server socket error — shutting down")
                break

    def stop(self):
        """Gracefully shut down the server.

        1. Stop accepting new connections.
        2. Close all active client handlers.
        3. Shut down the thread pool.
        4. Close the server socket.
        """
        if not self.is_running:
            return

        self.logger.info("Initiating graceful shutdown...")
        self.is_running = False

        # Close every active client connection
        with self._lock:
            for handler in self.clients:
                try:
                    handler.close()
                except Exception as e:
                    self.logger.debug(f"Error closing handler: {e}")
            self.clients.clear()

        # Shut down the worker thread pool (wait up to 5 s)
        try:
            self.thread_pool.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            # Python <3.9 does not support cancel_futures
            self.thread_pool.shutdown(wait=False)

        # Close the listening socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        uptime = time.time() - (self._started_at or time.time())
        self.logger.info(f"Server stopped (uptime {uptime:.1f}s)")

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _signal_handler(self, signum, frame):
        """Handle OS termination signals."""
        sig_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
        self.logger.info(f"Received {sig_name} — shutting down")
        self.stop()

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return a snapshot of server statistics.

        Returns:
            A dict with keys ``uptime``, ``active_clients``,
            ``total_bytes_sent``, ``total_bytes_received``, and a
            ``clients`` list with per-connection details.
        """
        with self._lock:
            active = [c for c in self.clients if c.is_active]
            client_info = [c.get_info() for c in active]
            total_sent = sum(c.bytes_sent for c in self.clients)
            total_recv = sum(c.bytes_received for c in self.clients)

        return {
            "host": self.host,
            "port": self.port,
            "uptime": time.time() - (self._started_at or time.time()),
            "is_running": self.is_running,
            "active_clients": len(client_info),
            "max_clients": self.max_clients,
            "total_bytes_sent": total_sent,
            "total_bytes_received": total_recv,
            "clients": client_info,
        }


# ----------------------------------------------------------------------
# CLI entry point
# ----------------------------------------------------------------------

def main():
    """Parse command-line arguments and start the HanogtVPN server."""
    parser = argparse.ArgumentParser(
        prog="hanogtvpn-server",
        description="HanogtVPN Server — secure VPN server with ECDH + RSA handshake",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Address to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--max-clients",
        type=int,
        default=50,
        help="Maximum simultaneous client connections (default: 50)",
    )

    args = parser.parse_args()

    server = VPNServer(
        host=args.host,
        port=args.port,
        max_clients=args.max_clients,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    except Exception as e:
        print(f"Fatal server error: {e}", file=sys.stderr)
        server.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
