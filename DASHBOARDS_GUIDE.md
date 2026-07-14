# Grafana Dashboards Guide

Drei vollständig ausgebaute Dashboards für Kamailio Monitoring, KPIs und Test-Analyse.

**URL**: http://localhost:3000 (admin/admin)

---

## 🎯 Dashboard Übersicht

| Dashboard | ID | Panels | Zweck | Refresh |
|-----------|----|----|---------|---------|
| **Main Monitoring** | `kamailio-main` | 15 | Echtzeit-Überwachung aller Metriken | 5s |
| **KPI Dashboard** | `kamailio-kpi` | 10 | Normierte Performance-Kennzahlen | 5s |
| **Test Analysis** | `kamailio-test-analysis` | 12 | Testlauf-Bewertung & Vergleich | 5s |

---

## 🔷 Main Monitoring Dashboard

**URL**: http://localhost:3000/d/kamailio-main

### Row 1: System Health & Memory (Collapsible)

| Panel | Typ | Metrik | Thresholds |
|-------|-----|--------|------------|
| Kamailio Status | Stat | `kamailio_up` | Online (✅ grün) / Offline (❌ rot) |
| Uptime | Stat | `kamailio_core_uptime_uptime_total` | grün/gelb/rot nach Dauer |
| SHM Usage % | Gauge | `shmmem_used / shmmem_total * 100` | ✅ <60% grün, ⚠️ 60-80% gelb, 🔴 >80% rot |
| Shared Memory Trend | TimeSeries | Used/Free/Peak Memory | Zeigt Memory-Leaks |
| SHM Fragments | TimeSeries | `kamailio_core_shmmem_fragments` | <500 ok, >1000 Problem |

**Interpretation:**
- SHM Usage sollte unter 60% bleiben
- Wenn Peak konstant steigt → Memory Leak!
- Fragments >1000 → Defragmentierung nötig

### Row 2: Transaction Manager (TM) - Calls & INVITEs

| Panel | Typ | Metrik | Zeigt |
|-------|-----|--------|-------|
| Total Transactions | Stat | `tm_stats_total_total` | Gesamtanzahl Transactions seit Start |
| Active Transactions | Stat | `tm_stats_current` | Aktuell aktive Calls |
| Transactions/sec | Stat | `rate(tm_stats_created_total[1m])` | Durchsatz (Calls/Sekunde) |
| TM Response Codes | TimeSeries | 2xx/4xx/5xx | Success vs. Error Trend |

**Interpretation:**
- `Active Transactions` sollte sich mit Load ändern
- Wenn bleibt hoch → Transactions stecken fest
- 2xx high = Healthy, 4xx/5xx = Probleme

### Row 3: Stateless Module (SL) - SIP Responses

| Panel | Typ | Metrik | Info |
|-------|-----|--------|------|
| 200 OK (Success) | Stat | `sl_codes{200}` | Erfolgreiche REGISTER/INVITE |
| 4xx Errors | Stat | `sl_codes{4xx}` | Client-Fehler (Request-Probleme) |
| 5xx Errors | Stat | `sl_codes{5xx}` | Server-Fehler (Kamailio-Probleme) |
| SL Response Distribution | TimeSeries | 200/202/4xx/5xx | Verhältnis Erfolg:Fehler |

**Interpretation:**
- Sollte hauptsächlich 200 OK sein
- 4xx ok wenn <5%
- 5xx = immer Problem

### Row 4: TCP & Network

| Panel | Typ | Metrik | Zeigt |
|-------|-----|--------|-------|
| TCP Connections | Stat | `tcp_info_opened_connections` | Offene TCP-Links gerade |
| TCP Limit | Stat | `tcp_info_max_connections` | Maximales Limit (2048) |
| TCP Write Queue | TimeSeries | `tcp_info_write_queued_bytes` | Gepufferte Daten zum Senden |
| TCP Status | TimeSeries | Open/Readers | Netzwerk-Aktivität |

---

## 📊 KPI Dashboard

**URL**: http://localhost:3000/d/kamailio-kpi

### Top Row: Core KPIs (Normiert)

| KPI | Formel | Gut | Warnung | Kritisch |
|-----|--------|------|---------|----------|
| **Success Rate %** | (200+202) / (200+202+4xx+5xx) × 100 | >95% ✅ | 80-95% ⚠️ | <80% 🔴 |
| **Memory Utilization %** | used / total × 100 | <60% ✅ | 60-80% ⚠️ | >80% 🔴 |
| **Throughput** | calls/sec (1m rate) | steigt mit Last | — | — |
| **Concurrent Calls** | active transactions | variabel | >100 ⚠️ | — |

### Trend Analysis

- **Call Rate Trend**: Transaktionen/sec + Success/sec
  - Zeigt, wie die Last variiert
  - Sollte korrekt hochfahren beim Test

- **Success Rate Trend**: % über Zeit
  - Sollte konstant >95% sein
  - Abfälle = Probleme

### Error Analysis

- **Client Errors**: 400, 401, 403, 404, 408
  - Meist Request-Probleme (SIP-Message-Format oder Kamailio Config)
  - Sollte niedrig bleiben

- **Server Errors**: 500er Fehler
  - 🔴 Immer ein Problem!
  - Kamailio crashed/overload?

### Resource Efficiency

- **Memory Efficiency**: calls/sec pro MB SHM
  - Höher = besser
  - Sollte konstant sein

- **Memory per Transaction**: bytes/transaction
  - Sollte konstant sein
  - Wenn steigt → Memory Leak!

---

## 🧪 Test Run Analysis Dashboard

**URL**: http://localhost:3000/d/kamailio-test-analysis

### Test Score Cards (Top)

| Metric | Bewertung | Gut | Warnung | Fail |
|--------|-----------|------|---------|------|
| **Success Rate** | Prozent | >95% | 80-95% | <80% |
| **Peak Memory** | Prozent of max | <50% | 50-80% | >80% |
| **Error Rate** | Prozent | <1% | 1-5% | >5% |
| **Avg Throughput** | calls/sec | steigt | stagniert | fällt |
| **Peak Concurrent** | active calls | passt zur Config | — | — |

### Request Timeline & Performance

- **Request Rate Over Time**: 
  - Transactions/sec + Success/sec + Errors/sec
  - Zeigt Profile während Test
  - Sollte mit Settings übereinstimmen

- **Active Transactions Over Time**:
  - Sollte bis max. `parallel` Parameter gehen
  - Danach konstant halten

### Results Breakdown

- **Result Summary**: Zahlen für Success/4xx/5xx
- **Result Distribution**: Pie Chart (Erfolg %)
- **Memory Profile**: Used + Peak Memory

### Error Details

- **Client Errors by Type**: Welche 4xx-Codes?
  - 400 = malformed request
  - 404 = user not found
  - 408 = timeout

- **Server Errors by Type**: Welche 5xx?
  - 500 = generic server error
  - Sollte idealerweise 0 sein

---

## 🎮 Wie man die Dashboards nutzt

### 1. **Während eines Tests**

1. Öffne **Main Monitoring** Dashboard
2. Beobachte:
   - Memory Trend (sollte stabil bleiben)
   - Active Transactions (sollte bis ~parallel gehen)
   - TM Response Codes (sollte 2xx hoch sein)
3. Öffne **KPI Dashboard** zusätzlich
   - Beobachte Success Rate % (sollte >95% sein)
   - Beobachte Throughput (sollte mit Rate übereinstimmen)

### 2. **Nach einem Test**

1. Öffne **Test Analysis Dashboard**
2. Schau die Scorecard an:
   - Success Rate: Wie viel % erfolgreich?
   - Peak Memory: War ich zu nah an Limit?
   - Error Rate: Wie viel % Fehler?
3. Vergleiche mit vorherigen Tests
4. Nutze Error Details um Probleme zu diagnostizieren

### 3. **Für Performance-Tuning**

1. Führe Light-Test durch → Check Main Dashboard
2. Notiere Peak Memory %
3. Führe Medium-Test durch → Check KPI Dashboard
4. Vergleiche Success Rate und Memory Utilization
5. Führe Heavy-Test durch → Check Test Analysis
6. Bewerte Overall Performance

---

## 📈 PromQL Queries (zum Anpassen)

Falls du eigene Panels hinzufügen möchtest:

### Memory-Queries

```promql
# Memory Usage %
(kamailio_core_shmmem_used / kamailio_core_shmmem_total) * 100

# Memory in MB
kamailio_core_shmmem_used / 1024 / 1024

# Memory Trend (Rate of Change)
rate(kamailio_core_shmmem_used[5m])
```

### Performance-Queries

```promql
# Calls per second
rate(kamailio_tm_stats_created_total[1m])

# Success rate
(kamailio_sl_stats_codes_total{code="200"} / 
 (kamailio_sl_stats_codes_total{code="200"} + 
  kamailio_sl_stats_codes_total{code="4xx"} + 
  kamailio_sl_stats_codes_total{code="5xx"})) * 100

# Error rate
(kamailio_sl_stats_codes_total{code="4xx"} / 
 kamailio_sl_stats_codes_total) * 100
```

### Connection-Queries

```promql
# Active Transactions
kamailio_tm_stats_current

# TCP Connections
kamailio_core_tcp_info_opened_connections
```

---

## 🎨 Dashboard Features

### Collapsible Rows
- Klick auf Row-Title um ein-/auszuklappen
- Spart Screen-Space wenn du nur ein Thema brauchst

### Refresh Rates
- Alle Dashboards: **5s Auto-Refresh**
- Zeitfenster: **1h Default** (letzte Stunde)
- Kannst du oben rechts ändern

### Tooltip Mode
- Hover über Punkt in Graph → Detailinfo
- "Multi" Mode = zeigt alle Series auf einmal

### Time Range
- Oben rechts: `now-1h` bis `now`
- Schnell-Optionen: 5m, 15m, 1h, 6h, 24h
- Oder: Custom Range

---

## 🔧 Dashboard anpassen

### Neue Panel hinzufügen

1. Klick "Add Panel" (+ oben rechts)
2. Wähle Panel-Type (Line, Stat, Gauge, Table, etc.)
3. Schreib PromQL Query
4. Stelle Title, Unit, Thresholds ein
5. Save

### Panel duplizieren

1. Klick "Menu" (drei Punkte oben rechts im Panel)
2. "Duplicate"
3. Bearbeite die neue Kopie

### Row Group erstellen

1. "Add Row"
2. Gib Title ein
3. Panels hinzufügen/verschieben
4. Kann ein-/ausgeklappt werden

---

## 📋 Checkliste für Tests

### Vor dem Test:
- [ ] Main Dashboard offen
- [ ] KPI Dashboard offen
- [ ] Memory Baseline notiert (sollte <5 MB sein)
- [ ] Alle Container laufen (`docker compose ps`)

### Während Light-Test:
- [ ] Memory steigt auf 5-10 MB
- [ ] Success Rate > 95%
- [ ] TM Transactions entsprechen Calls (50)
- [ ] SL 200 OK ≈ 50

### Während Medium-Test:
- [ ] Memory steigt auf 10-20 MB
- [ ] Success Rate > 95%
- [ ] Throughput konstant ~20 calls/sec
- [ ] Concurrent Transactions ≤ 50

### Während Heavy-Test:
- [ ] Memory steigt auf 20-50 MB
- [ ] Success Rate > 90%
- [ ] Throughput konstant ~50 calls/sec
- [ ] Peak Memory < 80%

### Nach Test:
- [ ] Memory fällt zurück (kein Leak!)
- [ ] No hanging Transactions
- [ ] Error Rate < 5%
- [ ] Alle Metriken konsistent

---

## 🚨 Fehlerbehebung

### Panel zeigt keine Daten

```
→ Prometheus nicht erreichbar?
  curl http://localhost:9494/metrics

→ Metrik-Name falsch?
  Check Metrics Reference

→ Zeitraum zu kurz?
  Stelle Dashboard auf "Last 5m" um
```

### Panel zeigt Error

```
→ PromQL Syntax Fehler?
  Gib Query in Prometheus Console ein

→ Datasource nicht konfiguriert?
  Settings → Data Sources → Check Prometheus
```

### Dashboards nicht sichtbar

```
→ Grafana neustarten
  docker compose restart grafana

→ Provisioning-Pfad prüfen
  ls /grafana/provisioning/dashboards/*.json
```

---

## 📚 Weitere Ressourcen

- [Metrics Reference](METRICS_REFERENCE.md) – Alle Metriken erklärt
- [Load Test Guide](LOAD_TEST_GUIDE.md) – Wie Tests laufen
- [Grafana Docs](https://grafana.com/docs/) – Grafana selbst
- [Prometheus Docs](https://prometheus.io/docs/) – PromQL
