# Release v1.1-encrypted: TLS/SRTP Encrypted Load Testing

**Release Date**: 2026-07-14  
**Tag**: `v1.1-encrypted`

## 🆕 Major Features

### 🔐 Encrypted/Unencrypted Load Testing Toggle
- **Global UI Control**: One-click switch between plaintext (UDP) and encrypted (TLS+SRTP) modes
- **No Mode Mixing**: All calls in a test use the same encryption mode for fair comparison
- **All Test Types Supported**: Presets (Light/Medium/Heavy), Custom, and Live Test modes all respect the toggle

### 🔒 TLS Signaling Support
- **Kamailio TLS Module**: Full integration with `tls.so` module (port 5061)
- **Automatic Certificates**: Self-signed CA + Kamailio server cert auto-generated on `docker compose up`
- **Per-Call Handshakes**: Each SIP call performs its own TLS handshake (worst-case stress test design)
- **10-Year Validity**: Certificates generated with proper SAN (`DNS:kamailio,DNS:localhost,IP:127.0.0.1`)

### 📊 SRTP-Style Media Encryption
- **Simplified SRTP**: AES-128-CTR encryption + HMAC-SHA1-80 authentication (not RFC 3711-compliant)
- **Realistic CPU Cost**: Real crypto operations, simplified key management (for load testing, not security)
- **Loopback Media**: Media packets exchanged directly between load-controller sockets (Kamailio never touches media)
- **Transparent to Kamailio**: Only TLS signaling overhead is visible in server dashboards

### 📈 Enhanced Monitoring
- **🔒/🔓 Emoji Badges**: Test annotations in Grafana show encryption status visually
- **Tagged Metrics**: Encryption mode included in Grafana annotation tags for filtering/analysis
- **Side-by-Side Comparison**: Run encrypted and unencrypted tests back-to-back to measure overhead

## 📋 Technical Details

| Aspect | Unencrypted | Encrypted |
|--------|---|---|
| **SIP Transport** | UDP:5060 | TLS/TCP:5061 |
| **RTP Media** | Plain packets | AES-128-CTR + HMAC-SHA1-80 |
| **Handshake** | None | Per-call |
| **Max Concurrent** | 2000 (OS limit) | 2000 (OS limit) |

## 🔧 Infrastructure Changes

### New Components
- **cert-init Service**: Alpine container running OpenSSL, idempotent certificate generation
- **Certificate Volume**: `./kamailio/tls/` stores CA key, Kamailio key+cert, CA cert
- **Transport Abstraction**: Python SIP client now has `UdpTransport` and `TlsTransport` classes

### Kamailio Configuration
```
listen=tls:0.0.0.0:5061
enable_tls=yes
tcp_children=8
tls_max_connections=4096
tls_threads_mode=1
```

### Docker Updates
- Load-controller ulimits raised to `nofile: 65536` (supports 2000 concurrent connections)
- Kamailio SHM memory increased from 128MB to 192MB (for TLS session state)

## 📚 Documentation

- **README.md**: Encryption modes overview, media handling, OS limits documentation
- **LOAD_CONTROLLER_README.md**: UI toggle description, encryption mode details
- **Code Comments**: Transport layer, SRTP implementation clearly marked as simplified/testing-only

## ⚙️ Known Limitations & Design Decisions

1. **Per-Call Handshakes** (not optimized): Each call opens a new TLS connection and performs full handshake. This is intentional worst-case design for stress testing.

2. **SRTP is Simplified** (not RFC 3711): No real MKI, no replay protection, no rollover counter. Sufficient for CPU cost measurement, not for security compliance.

3. **Media in load-controller Only**: Kamailio never processes media packets. Only SIP signaling (REGISTER/INVITE/ACK/BYE) goes through Kamailio on port 5061. This means media encryption cost shows in load-controller CPU, not Kamailio dashboards.

4. **2000 Concurrent Call Hard Cap**: Determined by OS ephemeral port limits (~28k/destination IP) and file descriptor limits. Live Test's "parallel" slider can request more, but actual concurrency is capped.

5. **Self-Signed Certificates**: Not trusted by external clients. Intended for controlled lab testing only. Verification disabled in client (`verify_certificate=0`).

## 🚀 Getting Started

```bash
# Start the stack with TLS support
docker compose up -d --build

# Open Web UI
open http://localhost:8080

# Toggle Encryption (radio buttons at top)
# 🔓 Unencrypted (UDP) - default
# 🔒 Encrypted (TLS + SRTP)

# Run tests and compare in Grafana
open http://localhost:3000/d/kamailio-test-analysis
```

## 🔄 Upgrade Path

Existing installations should:
1. `git pull` to get new cert-init and config changes
2. `docker compose down && docker compose up -d --build` to regenerate volumes and rebuild containers
3. Certificates are auto-generated; no manual steps required

## 🐛 Testing & Validation

- ✅ Kamailio TLS module loads and binds on port 5061
- ✅ Certificates auto-generated idempotently on each `docker compose up`
- ✅ UI toggle correctly passes encryption flag to all test endpoints
- ✅ Grafana annotations include 🔒/🔓 badges
- ✅ Max worker count hard-capped at 2000
- ✅ load-controller fd limits raised to support concurrent connections

## 📝 Commit

- **Hash**: `43e004c`
- **Message**: "Add TLS/SRTP encrypted load testing with global encryption toggle"
- **Files Changed**: 16 files, +712 insertions

---

**Questions?** Check the detailed docs in `README.md` and `LOAD_CONTROLLER_README.md` for architecture, limitations, and troubleshooting.
