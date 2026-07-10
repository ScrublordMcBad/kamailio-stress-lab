#!/usr/bin/env python3
"""
Simple SIP Load Generator
Sends REGISTER + INVITE/BYE sequences
"""

import socket
import time
import sys
from datetime import datetime

def send_sip(host, port, message):
    """Send raw SIP message"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(message.encode(), (host, port))
    sock.close()

def generate_register(user_id, kamailio_ip, client_ip, call_id_base):
    """Generate REGISTER message"""
    return f"""REGISTER sip:{kamailio_ip}:5060 SIP/2.0
Via: SIP/2.0/UDP {client_ip}:5061;branch=z9hG4bK776{user_id}
From: <sip:user{user_id}@{kamailio_ip}>;tag=1928301774
To: <sip:user{user_id}@{kamailio_ip}>
Call-ID: {call_id_base}@{client_ip}
CSeq: 1 REGISTER
Contact: <sip:user{user_id}@{client_ip}:5061>
Max-Forwards: 70
User-Agent: LoadGen/1.0
Content-Length: 0

"""

def generate_invite(user_id, kamailio_ip, client_ip, call_id_base):
    """Generate INVITE message"""
    return f"""INVITE sip:user{user_id}@{kamailio_ip}:5060 SIP/2.0
Via: SIP/2.0/UDP {client_ip}:5061;branch=z9hG4bK776inv{user_id}
From: <sip:user{user_id}@{client_ip}>;tag=inv{user_id}
To: <sip:user{user_id}@{kamailio_ip}>
Call-ID: inv{call_id_base}@{client_ip}
CSeq: 1 INVITE
Contact: <sip:user{user_id}@{client_ip}:5061>
Max-Forwards: 70
User-Agent: LoadGen/1.0
Content-Length: 0

"""

def run_load_test(kamailio_ip, rate, parallel, total_calls):
    """Run load test"""
    client_ip = "127.0.0.1"  # Will be seen as different when in container

    call_count = 0
    start_time = time.time()
    last_send_time = start_time

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting load test: {rate} calls/sec, {parallel} parallel, {total_calls} total")

    for i in range(total_calls):
        user_id = i % parallel
        call_id = f"{int(time.time())}_{i}"

        try:
            # Send REGISTER
            reg_msg = generate_register(user_id, kamailio_ip, client_ip, call_id)
            send_sip(kamailio_ip, 5060, reg_msg)

            time.sleep(0.01)  # Small delay

            # Send INVITE
            inv_msg = generate_invite(user_id, kamailio_ip, client_ip, call_id)
            send_sip(kamailio_ip, 5060, inv_msg)

            call_count += 1

            # Rate limiting
            elapsed = time.time() - start_time
            expected_time = call_count / rate
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)

            if call_count % 10 == 0:
                progress_pct = int((call_count / total_calls) * 100) if total_calls > 0 else 0
                print(f"PROGRESS:{call_count}/{total_calls}:{progress_pct}", flush=True)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {call_count}/{total_calls} calls sent", flush=True)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {call_count} calls in {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    kamailio_ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    parallel = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    total_calls = int(sys.argv[4]) if len(sys.argv) > 4 else 100

    run_load_test(kamailio_ip, rate, parallel, total_calls)
