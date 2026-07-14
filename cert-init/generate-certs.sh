#!/bin/sh
# Generate self-signed CA + Kamailio server cert for TLS testing.
# Idempotent: skips regeneration if a valid cert already exists.

set -euo pipefail

OUT=/certs-out
mkdir -p "$OUT"

# Check if cert already exists and is valid
if [ -s "$OUT/ca-cert.pem" ] && [ -s "$OUT/kamailio-cert.pem" ] && [ -s "$OUT/kamailio-key.pem" ]; then
    if openssl x509 -in "$OUT/kamailio-cert.pem" -checkend 0 -noout >/dev/null 2>&1; then
        echo "✅ Certs already present and valid, skipping generation"
        exit 0
    fi
fi

echo "🔐 Generating CA and Kamailio TLS certs..."

# Generate CA private key
openssl genrsa -out "$OUT/ca-key.pem" 2048 2>/dev/null

# Generate CA certificate (10 year validity)
openssl req -new -x509 -days 3650 -key "$OUT/ca-key.pem" -out "$OUT/ca-cert.pem" \
    -subj "/C=DE/ST=State/L=City/O=Test/CN=kamailio-ca" 2>/dev/null

# Generate Kamailio server key
openssl genrsa -out "$OUT/kamailio-key.pem" 2048 2>/dev/null

# Generate Kamailio server CSR with SAN
openssl req -new -key "$OUT/kamailio-key.pem" -out "$OUT/kamailio.csr" \
    -subj "/C=DE/ST=State/L=City/O=Test/CN=kamailio" \
    -addext "subjectAltName=DNS:kamailio,DNS:localhost,IP:127.0.0.1" 2>/dev/null

# Sign server cert with CA (10 year validity)
printf "subjectAltName=DNS:kamailio,DNS:localhost,IP:127.0.0.1" > "$OUT/san.ext"
openssl x509 -req -in "$OUT/kamailio.csr" \
    -CA "$OUT/ca-cert.pem" -CAkey "$OUT/ca-key.pem" \
    -CAcreateserial -out "$OUT/kamailio-cert.pem" \
    -days 3650 -extfile "$OUT/san.ext" \
    2>/dev/null
rm -f "$OUT/san.ext"

# Cleanup
rm -f "$OUT/kamailio.csr" "$OUT/ca-cert.srl" "$OUT/san.ext"

# Set permissions
chmod 644 "$OUT/ca-cert.pem" "$OUT/kamailio-cert.pem"
chmod 600 "$OUT/ca-key.pem" "$OUT/kamailio-key.pem"

echo "✅ Certs generated successfully in $OUT"
