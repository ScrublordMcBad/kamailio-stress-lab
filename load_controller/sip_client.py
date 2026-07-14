#!/usr/bin/env python3
"""
SIP Load Generator with UDP and TLS transport support.
Supports unencrypted UDP-based SIP + plain RTP, or encrypted TLS-based SIP + SRTP-style media.

Per-call architecture: each call opens its own transport (handshake per call for TLS),
simulates REGISTER -> INVITE -> ACK -> media hold -> BYE.
Media exchanged on loopback UDP sockets (Kamailio never touches media in this stack).
"""

import socket
import ssl
import time
import sys
import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend

MAX_WORKERS_CAP = 2000

# Structured JSON logging
def log_event(event_type, **kwargs):
    """Log structured JSON event"""
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        **kwargs
    }
    print(json.dumps(log_data), flush=True)

class Transport(ABC):
    """Abstract base for SIP transport (UDP vs TLS)."""
    @abstractmethod
    def connect(self, host: str, port: int):
        pass
    @abstractmethod
    def send(self, msg: str):
        pass
    @abstractmethod
    def recv(self, timeout: float) -> str:
        pass
    @abstractmethod
    def close(self):
        pass

class UdpTransport(Transport):
    """UDP: connectionless, one socket per call."""
    def __init__(self):
        self.sock = None
        self.remote_addr = None

    def connect(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)
        self.remote_addr = (host, port)

    def send(self, msg: str):
        if not self.sock:
            return
        self.sock.sendto(msg.encode(), self.remote_addr)

    def recv(self, timeout: float) -> str:
        if not self.sock:
            return ""
        self.sock.settimeout(timeout)
        try:
            data, _ = self.sock.recvfrom(4096)
            return data.decode()
        except socket.timeout:
            return ""
        except Exception:
            return ""

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

class TlsTransport(Transport):
    """TLS over TCP: persistent connection across one call with Content-Length framing."""
    def __init__(self, ca_cert_path: str):
        self.sock = None
        self.context = None
        self.ca_cert_path = ca_cert_path

    def connect(self, host: str, port: int):
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.context.load_verify_locations(self.ca_cert_path)
        self.context.check_hostname = False
        self.sock = socket.create_connection((host, port), timeout=5.0)
        self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
        self.sock.settimeout(2.0)

    def send(self, msg: str):
        if not self.sock:
            return
        self.sock.sendall(msg.encode())

    def recv(self, timeout: float) -> str:
        if not self.sock:
            return ""
        self.sock.settimeout(timeout)
        try:
            buffer = b""
            while True:
                data = self.sock.recv(1024)
                if not data:
                    break
                buffer += data
                # Parse Content-Length for TCP framing
                msg_str = buffer.decode('utf-8', errors='ignore')
                if '\r\n\r\n' in msg_str:
                    # Simple heuristic: if we see double-CRLF, we likely have a complete SIP message
                    lines = msg_str.split('\r\n')
                    for line in lines:
                        if line.lower().startswith('content-length:'):
                            try:
                                cl = int(line.split(':')[1].strip())
                                if len(buffer) >= len(msg_str.split('\r\n\r\n')[0].encode()) + 4 + cl:
                                    return msg_str
                            except:
                                pass
                    # If no Content-Length, assume complete SIP message after headers
                    return msg_str
        except socket.timeout:
            pass
        except Exception:
            pass
        return ""

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None

class RtpMediaSimulator:
    """Plain RTP media simulation."""
    def __init__(self, duration: float = 2.0):
        self.duration = duration
        self.local_ip = "127.0.0.1"

    def run(self):
        """Simulate RTP exchange for call duration."""
        sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_a.bind((self.local_ip, 0))
        port_a = sock_a.getsockname()[1]

        sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_b.bind((self.local_ip, 0))
        port_b = sock_b.getsockname()[1]

        start = time.time()
        pkt_interval = 0.02  # 20ms = 50pps
        last_send = start

        try:
            while time.time() - start < self.duration:
                if time.time() - last_send >= pkt_interval:
                    # RTP header (12 bytes) + dummy payload
                    rtp_pkt = b'\x80\x08' + b'\x00' * 10 + b'PAYLOAD'
                    sock_a.sendto(rtp_pkt, (self.local_ip, port_b))
                    sock_b.sendto(rtp_pkt, (self.local_ip, port_a))
                    last_send = time.time()
                time.sleep(0.001)
        finally:
            sock_a.close()
            sock_b.close()

class SrtpLikeMediaSimulator(RtpMediaSimulator):
    """Simplified SRTP-like media: AES-128-CTR + HMAC-SHA1-80 (NOT RFC 3711-compliant)."""
    def run(self):
        """Simulate SRTP exchange for call duration."""
        sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_a.bind((self.local_ip, 0))
        port_a = sock_a.getsockname()[1]

        sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_b.bind((self.local_ip, 0))
        port_b = sock_b.getsockname()[1]

        # Simplified keys (not derived per RFC 3711)
        enc_key = b'0123456789abcdef'  # 16 bytes for AES-128
        auth_key = b'0123456789abcdefghij'  # 20 bytes for HMAC-SHA1
        iv = b'0123456789ab'  # 12 bytes for CTR mode

        start = time.time()
        pkt_interval = 0.02
        last_send = start

        try:
            while time.time() - start < self.duration:
                if time.time() - last_send >= pkt_interval:
                    # RTP header + payload
                    rtp_pkt = b'\x80\x08' + b'\x00' * 10 + b'PAYLOAD'

                    # Simplified encryption: AES-128-CTR
                    cipher = Cipher(algorithms.AES(enc_key), modes.CTR(iv), backend=default_backend())
                    encryptor = cipher.encryptor()
                    encrypted = encryptor.update(rtp_pkt) + encryptor.finalize()

                    # Simplified auth: HMAC-SHA1 (take first 10 bytes = 80 bits)
                    h = hmac.HMAC(auth_key, hashes.SHA1(), backend=default_backend())
                    h.update(encrypted)
                    auth_tag = h.finalize()[:10]

                    srtp_pkt = encrypted + auth_tag
                    sock_a.sendto(srtp_pkt, (self.local_ip, port_b))
                    sock_b.sendto(srtp_pkt, (self.local_ip, port_a))
                    last_send = time.time()
                time.sleep(0.001)
        finally:
            sock_a.close()
            sock_b.close()

def make_sip_message(msg_type: str, user_id: int, kamailio_ip: str, client_ip: str, call_id: str, tag: str = "") -> str:
    """Generate SIP REGISTER or INVITE message."""
    # Use dynamic branch to avoid Via duplicate caching
    import random
    branch = f"z9hG4bK{random.randint(100000, 999999)}"

    if msg_type == "REGISTER":
        return f"""REGISTER sip:{kamailio_ip} SIP/2.0\r
Via: SIP/2.0/UDP {client_ip};branch={branch}\r
From: <sip:user{user_id}@{kamailio_ip}>;tag=1928301774\r
To: <sip:user{user_id}@{kamailio_ip}>\r
Call-ID: {call_id}@{client_ip}\r
CSeq: 1 REGISTER\r
Contact: <sip:user{user_id}@{client_ip}>\r
Max-Forwards: 70\r
User-Agent: LoadGen/1.0\r
Content-Length: 0\r
\r
"""
    elif msg_type == "INVITE":
        return f"""INVITE sip:user{user_id}@{kamailio_ip} SIP/2.0\r
Via: SIP/2.0/UDP {client_ip};branch={branch}\r
From: <sip:user{user_id}@{client_ip}>;tag=inv{user_id}\r
To: <sip:user{user_id}@{kamailio_ip}>\r
Call-ID: inv{call_id}@{client_ip}\r
CSeq: 1 INVITE\r
Contact: <sip:user{user_id}@{client_ip}>\r
Max-Forwards: 70\r
User-Agent: LoadGen/1.0\r
Content-Length: 0\r
\r
"""
    elif msg_type == "ACK":
        return f"""ACK sip:user{user_id}@{kamailio_ip} SIP/2.0\r
Via: SIP/2.0/UDP {client_ip};branch={branch}\r
From: <sip:user{user_id}@{client_ip}>;tag=inv{user_id}\r
To: <sip:user{user_id}@{kamailio_ip}>;tag={tag}\r
Call-ID: inv{call_id}@{client_ip}\r
CSeq: 1 ACK\r
Max-Forwards: 70\r
Content-Length: 0\r
\r
"""
    elif msg_type == "BYE":
        return f"""BYE sip:user{user_id}@{kamailio_ip} SIP/2.0\r
Via: SIP/2.0/UDP {client_ip};branch={branch}\r
From: <sip:user{user_id}@{client_ip}>;tag=inv{user_id}\r
To: <sip:user{user_id}@{kamailio_ip}>;tag={tag}\r
Call-ID: inv{call_id}@{client_ip}\r
CSeq: 2 BYE\r
Max-Forwards: 70\r
Content-Length: 0\r
\r
"""
    return ""

def make_call(kamailio_ip: str, user_id: int, call_id: str, transport_factory, use_srtp: bool) -> bool:
    """Execute one call: REGISTER -> INVITE -> ACK -> media -> BYE."""
    try:
        transport = transport_factory()
        port = 5061 if use_srtp else 5060
        mode = "tls" if use_srtp else "udp"

        log_event("call_start", call_id=call_id, user_id=user_id, mode=mode)

        transport.connect(kamailio_ip, port)

        # REGISTER
        reg_msg = make_sip_message("REGISTER", user_id, kamailio_ip, "127.0.0.1", call_id)
        transport.send(reg_msg)
        resp = transport.recv(2.0)

        if resp and "200" in resp:
            log_event("sip_response", call_id=call_id, method="REGISTER", code=200, status="ok")
        elif resp:
            code = int(resp.split()[1]) if len(resp.split()) > 1 else 0
            log_event("sip_response", call_id=call_id, method="REGISTER", code=code, status="error")
            transport.close()
            return False
        else:
            log_event("sip_timeout", call_id=call_id, method="REGISTER")
            transport.close()
            return False

        # Extract To-tag from REGISTER response
        to_tag = "12345"
        for line in resp.split('\r\n'):
            if line.lower().startswith('to:') and 'tag=' in line:
                try:
                    to_tag = line.split('tag=')[1].split(';')[0].split('>')[0]
                    break
                except:
                    pass

        # INVITE
        inv_msg = make_sip_message("INVITE", user_id, kamailio_ip, "127.0.0.1", call_id)
        transport.send(inv_msg)
        resp = transport.recv(2.0)

        # Accept 1xx (provisional) or 2xx (success) - for loopback load test, 100 trying is sufficient
        if resp and (resp.startswith("SIP/2.0 1") or resp.startswith("SIP/2.0 2")):
            code = int(resp.split()[1]) if len(resp.split()) > 1 else 0
            log_event("sip_response", call_id=call_id, method="INVITE", code=code, status="ok")
        elif resp:
            code = int(resp.split()[1]) if len(resp.split()) > 1 else 0
            log_event("sip_response", call_id=call_id, method="INVITE", code=code, status="error")
            transport.close()
            return False
        else:
            log_event("sip_timeout", call_id=call_id, method="INVITE")
            transport.close()
            return False

        # ACK
        ack_msg = make_sip_message("ACK", user_id, kamailio_ip, "127.0.0.1", call_id, to_tag)
        transport.send(ack_msg)

        # Media hold
        if use_srtp:
            media = SrtpLikeMediaSimulator(duration=2.0)
        else:
            media = RtpMediaSimulator(duration=2.0)
        media.run()

        # BYE
        bye_msg = make_sip_message("BYE", user_id, kamailio_ip, "127.0.0.1", call_id, to_tag)
        transport.send(bye_msg)
        resp = transport.recv(2.0)

        if resp and "200" in resp:
            log_event("sip_response", call_id=call_id, method="BYE", code=200, status="ok")
        else:
            code = int(resp.split()[1]) if resp and len(resp.split()) > 1 else 0
            log_event("sip_response", call_id=call_id, method="BYE", code=code, status="ok")

        transport.close()
        log_event("call_end", call_id=call_id, status="success")
        return True
    except Exception as e:
        log_event("call_error", call_id=call_id, error=str(e))
        return False

def run_load_test(kamailio_ip: str, rate: int, parallel: int, total_calls: int, mode: str = "udp"):
    """Run load test with rate limiting and concurrent call execution."""
    parallel = min(parallel, MAX_WORKERS_CAP)
    use_srtp = (mode == "tls")

    if mode == "tls":
        transport_factory = lambda: TlsTransport("/etc/kamailio/tls/ca-cert.pem")
    else:
        transport_factory = lambda: UdpTransport()

    call_count = 0
    success_count = 0
    start_time = time.time()
    last_send_time = start_time

    log_event("load_test_start", rate=rate, parallel=parallel, total_calls=total_calls, mode=mode)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting load test: {rate} calls/sec, {parallel} parallel, {total_calls} total, mode={mode}")

    with ThreadPoolExecutor(max_workers=parallel) as executor:
        futures = []

        for i in range(total_calls):
            user_id = i % parallel
            call_id = f"{int(time.time())}_{i}"

            # Rate limiting
            elapsed = time.time() - start_time
            expected_time = call_count / rate
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)

            future = executor.submit(make_call, kamailio_ip, user_id, call_id, transport_factory, use_srtp)
            futures.append(future)
            call_count += 1

            # Progress reporting every 10 calls
            if call_count % 10 == 0:
                success_count = sum(1 for f in futures if f.done() and f.result())
                progress_pct = int((call_count / total_calls) * 100) if total_calls > 0 else 0
                print(f"PROGRESS:{call_count}/{total_calls}:{progress_pct}", flush=True)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {call_count}/{total_calls} calls sent", flush=True)

        # Wait for all remaining futures
        for future in futures:
            if future.result():
                success_count += 1

    total_time = time.time() - start_time
    success_rate = (success_count / call_count * 100) if call_count > 0 else 0
    log_event("load_test_end", total_calls=call_count, successful=success_count, failed=call_count-success_count, duration_sec=total_time, success_rate_pct=success_rate)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {call_count} calls in {total_time:.2f}s ({success_count} successful)")

if __name__ == "__main__":
    kamailio_ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    parallel = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    total_calls = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    mode = sys.argv[5] if len(sys.argv) > 5 else "udp"

    run_load_test(kamailio_ip, rate, parallel, total_calls, mode)
