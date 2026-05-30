"""
HanogtVPN Client Connection Handler

Manages individual client connections including the ECDH + RSA
cryptographic handshake, encrypted data forwarding, heartbeat
monitoring, and connection lifecycle.
"""

import threading
import socket
import time
import json
import struct

from hanogtvpn.core.constants import (
    PacketType,
    BUFFER_SIZE,
    HEARTBEAT_INTERVAL,
    CONNECTION_TIMEOUT,
    ConnectionState,
)
from hanogtvpn.core.crypto import CryptoEngine
from hanogtvpn.core.protocol import VPNProtocol
from hanogtvpn.core.logger import VPNLogger


class ClientHandler:
    """Handles individual client connections with crypto handshake and data forwarding.

    Lifecycle:
        1. ``handle()`` is called by the server thread pool.
        2. A ECDH + RSA handshake is performed to derive a shared session key.
        3. Encrypted data packets are received, decrypted, and echoed back
           (production deployments would forward to a TUN/TAP interface).
        4. Heartbeat packets keep the session alive; a missed heartbeat
           beyond ``CONNECTION_TIMEOUT`` triggers automatic disconnection.
    """

    def __init__(
        self,
        client_socket: socket.socket,
        client_address: tuple,
        rsa_private_key,
        rsa_public_key,
        crypto_engine: CryptoEngine,
    ):
        self.client_socket = client_socket
        self.client_address = client_address
        self.rsa_private_key = rsa_private_key
        self.rsa_public_key = rsa_public_key
        self.crypto = crypto_engine
        self.session_key: bytes | None = None  # Derived after handshake
        self.state = ConnectionState.CONNECTING
        self.is_active = True
        self.logger = VPNLogger.get_logger("handler")
        self.connected_at = time.time()
        self.last_heartbeat = time.time()
        self.bytes_sent = 0
        self.bytes_received = 0
        self._heartbeat_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(self):
        """Main handler loop — perform handshake then forward data."""
        try:
            self.logger.info(
                f"Starting handshake with {self.client_address[0]}:{self.client_address[1]}"
            )
            if not self._perform_handshake():
                self.logger.error(f"Handshake failed for {self.client_address}")
                self._send_error("Handshake failed")
                self.close()
                return

            self.state = ConnectionState.CONNECTED
            self.logger.info(
                f"Handshake successful for {self.client_address[0]}:{self.client_address[1]}"
            )

            # Start heartbeat monitor in a background daemon thread
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_checker,
                daemon=True,
                name=f"heartbeat-{self.client_address[0]}:{self.client_address[1]}",
            )
            self._heartbeat_thread.start()

            self._data_loop()
        except Exception as e:
            self.logger.error(f"Handler error for {self.client_address}: {e}")
        finally:
            self.close()

    def close(self):
        """Clean up connection and release resources."""
        if not self.is_active:
            return
        self.is_active = False
        self.state = ConnectionState.DISCONNECTED

        try:
            self.client_socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # Socket may already be closed

        try:
            self.client_socket.close()
        except OSError:
            pass

        duration = time.time() - self.connected_at
        self.logger.info(
            f"Connection closed for {self.client_address[0]}:{self.client_address[1]} "
            f"(duration={duration:.1f}s, sent={self.bytes_sent}, recv={self.bytes_received})"
        )

    def get_info(self) -> dict:
        """Return a snapshot of this handler's connection info."""
        return {
            "address": f"{self.client_address[0]}:{self.client_address[1]}",
            "state": self.state.name if hasattr(self.state, "name") else str(self.state),
            "connected_at": self.connected_at,
            "uptime": time.time() - self.connected_at,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "is_active": self.is_active,
        }

    # ------------------------------------------------------------------
    # Handshake
    # ------------------------------------------------------------------

    def _perform_handshake(self) -> bool:
        """ECDH + RSA handshake protocol (server side).

        Steps:
            1. Receive the client's HANDSHAKE_REQUEST containing the client's
               ECDH public key bytes.
            2. Generate the server's own ECDH keypair.
            3. Derive the shared secret (session key) from the server's ECDH
               private key and the client's ECDH public key.
            4. Sign the server's ECDH public key bytes with the RSA private key.
            5. Send a HANDSHAKE_RESPONSE containing the server's ECDH public
               key, the RSA signature, and the server's RSA public key PEM.

        Returns:
            ``True`` on success, ``False`` on any failure.
        """
        try:
            # Set a generous timeout for the handshake phase
            self.client_socket.settimeout(CONNECTION_TIMEOUT)

            # --- Step 1: Receive client ECDH public key -----------------
            pkt_type, payload = VPNProtocol.recv_packet(self.client_socket)
            if pkt_type != PacketType.HANDSHAKE_REQUEST:
                self.logger.warning(
                    f"Expected HANDSHAKE_REQUEST from {self.client_address}, "
                    f"got {pkt_type}"
                )
                return False

            client_ecdh_pub_bytes = payload
            if not client_ecdh_pub_bytes:
                self.logger.warning("Empty ECDH public key from client")
                return False

            self.logger.debug(
                f"Received client ECDH public key ({len(client_ecdh_pub_bytes)} bytes)"
            )

            # --- Step 2: Generate server ECDH keypair -------------------
            server_ecdh_pub_bytes, server_ecdh_priv_key = (
                self.crypto.generate_ecdh_keypair()
            )

            # --- Step 3: Derive shared secret ---------------------------
            self.session_key = self.crypto.derive_shared_secret(
                server_ecdh_priv_key, client_ecdh_pub_bytes
            )
            self.logger.debug("Session key derived successfully")

            # --- Step 4: RSA-sign the server ECDH public key ------------
            rsa_signature = self.crypto.sign_data(
                self.rsa_private_key, server_ecdh_pub_bytes
            )

            # --- Step 5: Build and send HANDSHAKE_RESPONSE --------------
            server_rsa_pem = self.crypto.serialize_public_key(self.rsa_public_key)

            response_data = VPNProtocol.create_handshake_response(
                server_ecdh_pub_bytes, rsa_signature, server_rsa_pem
            )
            self.client_socket.sendall(response_data)

            self.last_heartbeat = time.time()
            return True

        except socket.timeout:
            self.logger.warning(f"Handshake timed out for {self.client_address}")
            return False
        except ConnectionResetError:
            self.logger.warning(
                f"Connection reset during handshake with {self.client_address}"
            )
            return False
        except Exception as e:
            self.logger.error(f"Handshake exception for {self.client_address}: {e}")
            return False

    # ------------------------------------------------------------------
    # Data loop
    # ------------------------------------------------------------------

    def _data_loop(self):
        """Main data forwarding loop after a successful handshake.

        Handles three packet types:
            * DATA — decrypt, process (echo back), and re-encrypt.
            * HEARTBEAT — update the last-seen timestamp.
            * DISCONNECT — graceful client-initiated shutdown.
        """
        self.client_socket.settimeout(HEARTBEAT_INTERVAL * 3)

        while self.is_active:
            try:
                pkt_type, payload = VPNProtocol.recv_packet(
                    self.client_socket, self.crypto, self.session_key
                )

                if pkt_type is None:
                    # Connection closed by peer
                    self.logger.info(
                        f"Connection closed by {self.client_address[0]}:{self.client_address[1]}"
                    )
                    break

                self.last_heartbeat = time.time()

                if pkt_type == PacketType.DATA:
                    self._handle_data(payload)

                elif pkt_type == PacketType.HEARTBEAT:
                    self.logger.debug(
                        f"Heartbeat from {self.client_address[0]}:{self.client_address[1]}"
                    )
                    # Respond with a heartbeat acknowledgement
                    heartbeat_resp = VPNProtocol.create_heartbeat()
                    self.client_socket.sendall(heartbeat_resp)

                elif pkt_type == PacketType.DISCONNECT:
                    self.logger.info(
                        f"Client {self.client_address[0]}:{self.client_address[1]} "
                        f"requested disconnect"
                    )
                    break

                elif pkt_type == PacketType.ERROR:
                    self.logger.warning(
                        f"Error packet from {self.client_address[0]}:{self.client_address[1]}: "
                        f"{payload}"
                    )
                    break

                else:
                    self.logger.warning(
                        f"Unknown packet type {pkt_type} from {self.client_address}"
                    )

            except socket.timeout:
                # Check if client is still alive via heartbeat timestamp
                if time.time() - self.last_heartbeat > CONNECTION_TIMEOUT * 3:
                    self.logger.warning(
                        f"Client {self.client_address[0]}:{self.client_address[1]} "
                        f"timed out (no heartbeat)"
                    )
                    break
                continue

            except ConnectionResetError:
                self.logger.info(
                    f"Connection reset by {self.client_address[0]}:{self.client_address[1]}"
                )
                break

            except OSError as e:
                if self.is_active:
                    self.logger.error(f"Socket error in data loop: {e}")
                break

            except Exception as e:
                self.logger.error(
                    f"Unexpected error in data loop for {self.client_address}: {e}"
                )
                break

    def _handle_data(self, payload: bytes):
        """Process a decrypted DATA payload.

        In the current implementation data is echoed back to the client.
        A production deployment would forward the payload to a TUN/TAP
        interface and route it to the destination network.
        """
        if not payload:
            return

        with self._lock:
            self.bytes_received += len(payload)

        # --- Echo mode (replace with TUN/TAP forwarding in production) ---
        response = VPNProtocol.create_packet(
            PacketType.DATA, payload, self.crypto, self.session_key
        )
        try:
            self.client_socket.sendall(response)
            with self._lock:
                self.bytes_sent += len(payload)
        except OSError as e:
            self.logger.error(f"Failed to send data to {self.client_address}: {e}")
            self.is_active = False

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    def _heartbeat_checker(self):
        """Periodically send heartbeat packets and monitor client liveness.

        Runs in a daemon thread and exits when the handler is no longer
        active.
        """
        while self.is_active:
            try:
                time.sleep(HEARTBEAT_INTERVAL)

                if not self.is_active:
                    break

                # Check if client has missed too many heartbeats
                elapsed = time.time() - self.last_heartbeat
                if elapsed > CONNECTION_TIMEOUT * 3:
                    self.logger.warning(
                        f"Client {self.client_address[0]}:{self.client_address[1]} "
                        f"heartbeat timeout ({elapsed:.1f}s)"
                    )
                    self.is_active = False
                    break

                # Send a heartbeat probe to the client
                try:
                    heartbeat_pkt = VPNProtocol.create_heartbeat()
                    self.client_socket.sendall(heartbeat_pkt)
                    self.logger.debug(
                        f"Heartbeat sent to {self.client_address[0]}:{self.client_address[1]}"
                    )
                except OSError:
                    self.logger.warning(
                        f"Failed to send heartbeat to {self.client_address[0]}:{self.client_address[1]}"
                    )
                    self.is_active = False
                    break

            except Exception as e:
                self.logger.error(f"Heartbeat checker error: {e}")
                break

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _send_error(self, message: str):
        """Send an ERROR packet to the client (best-effort)."""
        try:
            error_payload = message.encode("utf-8")
            pkt = VPNProtocol.create_packet(PacketType.ERROR, error_payload)
            self.client_socket.sendall(pkt)
        except OSError:
            pass  # Connection may already be broken
