# Kamailio Load Test Controller

Web-basierter Load-Test Controller zum gezielten Triggern von SIP-Last gegen Kamailio.

## Features

✅ **Web UI** – Intuitive Oberfläche (Presets / Custom / Live Test)
✅ **Presets** – Light / Medium / Heavy (vordefinierte Lasten)
✅ **Custom** – Rate, Parallel, Total Calls frei konfigurierbar
✅ **Live Test** – Dynamische Last mit Ramp-up/Peak/Sawtooth-Patterns
✅ **On-Demand** – Tests starten/stoppen wie gewünscht
✅ **Live Monitoring** – Status in Echtzeit + Grafana Annotations
✅ **Auto-Annotations** – Test-Start/End in Grafana automatisch markiert mit 🔒/🔓 Emoji
✅ **Encrypted/Unencrypted Toggle** – Wechsel zwischen UDP (plain) und TLS+SRTP modes auf globaler Ebene

## Quickstart

```bash
# 1. Stack starten
docker compose up -d

# 2. Load Controller öffnen
open http://localhost:8080

# 3. Test wählen (Presets / Custom / Live Test) → Starten
# 4. Metriken in Grafana beobachten (http://localhost:3000)
```

## Encryption Modes (🔓/🔒)

**Globales Umschalter-UI** oben im Load Controller wählt zwischen:

### 🔓 Unencrypted (UDP)
- **SIP Transport**: UDP on Port 5060
- **Media**: Plain RTP packets (12-byte header only)
- **Handshake**: Keine
- **Nutzung**: Baseline-Vergleich, Legacy-Szenarien

### 🔒 Encrypted (TLS + SRTP-ähnlich)
- **SIP Transport**: TLS/TCP on Port 5061 (per-call handshake)
- **Media**: AES-128-CTR encrypted + HMAC-SHA1-80 authenticated (vereinfacht, nicht RFC 3711)
- **Handshake**: Ja, pro Call (worst-case Szenario)
- **Nutzung**: Verschlüsselungs-Overhead Assessment

**Wichtig**: Beide Modi können nicht gemischt werden. Alle Calls in einem Test nutzen den gleichen Modus. Die Encryption-Status wird in Grafana Annotations angezeigt (🔒/🔓 Badge).

## Test-Modi

### 1. Presets (Light / Medium / Heavy)

| Mode | Rate | Parallel | Calls | Duration | Use Case |
|------|------|----------|-------|----------|----------|
| **Light** | 5/sec | 10 | 500 | ~100s | Baseline |
| **Medium** | 20/sec | 50 | 2.000 | ~100s | Normal Load |
| **Heavy** | 50/sec | 100 | 5.000 | ~100s | Stress Test |

### 2. Custom

- **Rate**: 1–10.000 calls/sec
- **Parallel**: 1–20.000 concurrent
- **Calls**: 10–1.000.000 total
- Duration berechnet automatisch

### 3. Live Test (Neu)

- **Nutzer**: 1.000–1.000.000 (skalierbar)
- **Dauer**: 1–60 Minuten
- **Patterns**:
  - **Ramp-up**: 10% → 100% (realistische Tagesauslastung)
  - **Peak**: Build-up → Peak → Fallback (Überlast-Szenario)
  - **Sawtooth**: Oszillierende Last (40–90%)

## Web UI

**URL**: http://localhost:8080

### Linke Seite: Test Kontrolle
- **Encryption Toggle** (oben): 🔓 Unencrypted (UDP) oder 🔒 Encrypted (TLS+SRTP) wählen
- **Tabs**: Presets / Custom / Live Test
- Profil wählen oder Parameter setzen
- "Start Test" Button → Test läuft sofort mit dem gewählten Encryption Mode

### Rechte Seite: Active Tests
- Liste aller laufenden/abgeschlossenen Tests
- Status: `running` → `completed` oder `stopped`
- Countdown für verbleibende Zeit
- Stopp-Button für aktive Tests
- `Clear History` – Löscht alle Test-Einträge

### Quick Links
- **Metrics Endpoint** – http://localhost:9494/metrics
- **Prometheus** – http://localhost:9090
- **Grafana** – http://localhost:3000 (admin/admin)
- **Test Analysis Dashboard** – http://localhost:3000/d/kamailio-test-analysis

## REST API

```bash
# Profile abrufen
curl http://localhost:8080/api/profiles

# Preset Test starten (light/medium/heavy)
curl -X POST http://localhost:8080/api/run/light

# Custom Test starten
curl -X POST http://localhost:8080/api/run/custom \
  -H "Content-Type: application/json" \
  -d '{"rate": 100, "parallel": 50, "calls": 5000}'

# Live Test starten
curl -X POST http://localhost:8080/api/run/live \
  -H "Content-Type: application/json" \
  -d '{"users": 50000, "duration": 10, "pattern": "ramp-up"}'

# Dauer schätzen
curl -X POST http://localhost:8080/api/estimate-duration \
  -H "Content-Type: application/json" \
  -d '{"rate": 20, "calls": 2000}'

# Status abrufen
curl http://localhost:8080/api/status

# Test stoppen
curl -X POST http://localhost:8080/api/stop/<test_id>

# Verlauf löschen
curl -X POST http://localhost:8080/api/clear
```

## Was passiert beim Test?

Jeder Test führt aus (pro Calls):

1. **REGISTER** – User registriert sich bei Kamailio
2. **INVITE** – User ruft sich selbst an (Loopback)
3. **200 OK** – Call wird angenommen
4. **ACK** – Bestätigung
5. **BYE** – Call wird beendet
6. Speicher wird freigegeben

### Erwartete Metriken

| Metrik | Verhalten |
|--------|-----------|
| `tm.stats` (Transaction Manager) | Steigt während Test, zeigt aktive Transactions |
| `sl.stats` (Stateless) | 200 OK, 100 Trying responses |
| `core.shmmem_used_size` | Wächst bei REGISTERs, fällt nach Test |
| `core.shmmem_fragments` | Zeigt Speicherfragmentierung |

## Debugging

### Logs des Load Controller
```bash
docker logs -f load_controller
```

Wichtige Log-Marker:
- `✅ Annotation created` – Test Start/End wurde in Grafana markiert
- `📍 Monitor started/finished` – Test-Überwachung läuft/beendet
- `❌ stderr:` – Fehler im sip_client.py

### Kamailio Logs
```bash
docker logs -f kamailio | grep -E "INVITE|REGISTER|BYE"
```

### sip_client.py Output
```bash
# Direkt im Load Controller Log sichtbar:
docker logs load_controller | grep "stdout:"
```

### Prometheus Queries
```
# Transaction Rate
rate(kamailio_tm_stats_total[1m])

# Speichernutzung
kamailio_core_shmmem_used_size

# Erfolgsrate
rate(kamailio_sl_200_total[5m]) / 
(rate(kamailio_sl_200_total[5m]) + rate(kamailio_sl_4xx_total[5m]) + rate(kamailio_sl_5xx_total[5m]))
```

## Troubleshooting

### Controller startet nicht
```bash
docker logs load_controller
```

### Tests starten nicht
```bash
# Kamailio läuft?
docker ps | grep kamailio

# Netzwerk ok?
docker exec load_controller ping kamailio

# Prozess-Fehler?
docker logs load_controller | grep "❌\|stderr"
```

### Annotations fehlen in Grafana
```bash
# Grafana erreichbar?
curl -s http://localhost:3000/api/health

# Annotation-Logs checken
docker logs load_controller | grep "Annotation"
```

### Metriken werden nicht aktualisiert
```bash
# Exporter läuft?
docker logs kamailio_exporter

# Kamailio antwortet?
docker exec kamailio /usr/sbin/kamctl stats tm
```

## Architektur

```
┌─────────────────────────────────────┐
│     Load Controller Web UI (8080)   │
│     - Presets / Custom / Live Test  │
└──────────────────┬──────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
    ┌────────────┐      ┌──────────────┐
    │ sip_client │      │ sip_client   │ (mehrere pro Live-Phase)
    │  (Python)  │      │  (Python)    │
    └──────┬─────┘      └────────┬─────┘
           │                    │
           └────────┬───────────┘
                    ▼
           ┌────────────────────┐
           │  Kamailio (5060)   │ (UDP/TCP SIP)
           └──────────┬─────────┘
                      │ BINRPC/2049
                      ▼
           ┌────────────────────┐
           │ Kamailio Exporter  │ (9494)
           └──────────┬─────────┘
                      │ Scrape
                      ▼
           ┌────────────────────┐
           │  Prometheus (9090) │
           └──────────┬─────────┘
                      │ Query
                      ▼
           ┌────────────────────┐
           │  Grafana (3000)    │
           │ - Main Dashboard   │
           │ - KPI Dashboard    │
           │ - Test Analysis    │
           │ - Annotations      │
           └────────────────────┘
```
