# Load-Test Guide für Kamailio + Exporter

## 🎯 Schnelleinstieg: Load Controller (Web UI)

**Empfohlener Weg:** Grafische Web-Oberfläche zum Triggern von Load-Tests

```bash
# 1. Stack läuft bereits (docker compose up -d)
# 2. Browser öffnen
open http://localhost:8080

# 3. Test-Modus wählen:
#    - Presets: Light/Medium/Heavy (vordefiniert)
#    - Custom: Rate/Parallel/Calls manuell
#    - Live Test: Realistische Auslastung mit dynamischer Last
# 4. Test starten → Metriken live in Grafana http://localhost:3000
```

→ [Komplette Anleitung](LOAD_CONTROLLER_README.md)

---

## Test-Modi

### 1. **Presets** (Light / Medium / Heavy)
- **Light**: 5 calls/sec, 10 parallel, 500 total → ~90 Sekunden
- **Medium**: 20 calls/sec, 50 parallel, 2.000 total → ~90 Sekunden  
- **Heavy**: 50 calls/sec, 100 parallel, 5.000 total → ~90 Sekunden

**Best für**: Schnelle Standard-Tests, Baseline-Vergleiche

---

### 2. **Custom** (Freie Parameter)
- Rate: 1–10.000 calls/sec
- Parallel: 1–20.000 concurrent
- Total Calls: 10–1.000.000

**Best für**: Zielgerichtete Last-Tests, Performance-Tuning

---

### 3. **Live Test** (Dynamische Last)
- Skalierbare Nutzeranzahl: 1.000–1.000.000 (default 40.000)
- Testdauer: 1–60 Minuten
- Load-Patterns:
  - **Ramp-up**: Linear 10% → 100% (realistische Tagesauslastung)
  - **Peak**: Build-up → Peak → Fallback (Überlast-Szenario)
  - **Sawtooth**: Oszillierende Last (variable Auslastung)

**Best für**: Infrastruktur-Bewertung, Auslastungs-Szenarien, Stabilitäts-Tests

---

## Ziele beim Load-Testing

- **REGISTER**: Mehrere User registrieren sich
- **INVITE**: Parallele Calls zwischen den Usern
- **Shared Memory**: Verhalten des SHM-Speichers unter Last beobachten
- **Response-Zeiten**: Latenz und Durchsatz messen
- **Fehlerrate**: Wie verhält sich die Infrastruktur unter Last?

---

## Metriken beobachten

### Grafana Dashboards
- **URL**: http://localhost:3000 (admin/admin)
- **Kamailio Main**: System Health, Memory, Transactions, TCP
- **Kamailio KPI**: Success Rate, Throughput, Memory Efficiency
- **Kamailio Test Analysis**: Test Run Details, Error Analysis

### Live Metrics (Terminal)

```bash
# Alle Metrics vom Exporter
curl http://localhost:9494/metrics

# Nur relevante Metrics
curl -s http://localhost:9494/metrics | grep -E 'tm_|sl_|shmmem'

# Watch Mode (aktualisiert jede Sekunde)
watch -n 1 'curl -s http://localhost:9494/metrics | grep -E "(tm_|sl_|shmmem)'
```

### Direkter Kamailio Check (BINRPC)

```bash
# Im Kamailio-Container
docker exec kamailio /usr/sbin/kamctl stats tm
docker exec kamailio /usr/sbin/kamctl stats sl
docker exec kamailio /usr/sbin/kamctl stats core
```

---

## Shared Memory Verhalten

**Erwartung**:
- **core.shmmem_used_size** steigt beim Laden von REGISTERs
- **tm.stats** zeigen aktive Transactions (INVITE, ACK, BYE)
- Nach Test sollte Speicher wieder freigegeben werden

**Probleme erkennen**:
- Shared Memory wächst, kommt nicht runter → **Memory Leak**
- tm.stats bleiben stehen (keine 200 OK) → **Kamailio antwortet nicht**
- sl.stats 4xx/5xx hoch → **Requests scheitern**
- High fragmentation → **Memory-Effizienz Problem**

---

## Debugging

### Kamailio Logs
```bash
docker logs -f kamailio
```

### Load Controller Logs
```bash
docker logs -f load_controller
```

### Prometheus Abfrage (PromQL)
```
# Speichernutzung über Zeit
rate(kamailio_core_shmmem_used_size[1m])

# Transaction Rate
rate(kamailio_tm_stats_total[1m])

# Success Rate
100 * rate(kamailio_sl_200_total[5m]) / 
(rate(kamailio_sl_200_total[5m]) + rate(kamailio_sl_4xx_total[5m]) + rate(kamailio_sl_5xx_total[5m]))
```

---

## 💡 Empfehlungen

| Zweck | Modus | Warum |
|-------|-------|-------|
| Tägliche Regression-Tests | Presets | Schnell, reproduzierbar, standardisiert |
| Performance-Tuning | Custom | Genaue Kontrolle über Parameter |
| Infrastruktur-Bewertung | Live Test | Realistisches Verhalten, skalierbar |
| One-Shot Debugging | Terminal/Logs | Direkte Kontrolle, detaillierte Ausgaben |
