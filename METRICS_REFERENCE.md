# Kamailio Metrics Reference

Alle verfügbaren Prometheus Metriken vom Kamailio Exporter mit Erklärungen.

**URL**: http://localhost:9494/metrics

---

## 🔷 Core / Allgemein

| Metrik | Typ | Einheit | Bedeutung | Beispiel |
|--------|-----|--------|-----------|----------|
| `kamailio_up` | gauge | bool | Exporter erreichbar (1=Ja, 0=Nein) | `1` |
| `kamailio_core_uptime_uptime_total` | counter | Sekunden | Kamailio läuft seit... | `258` = 4m 18s |
| `kamailio_exporter_total_scrapes` | counter | Requests | Gesamt Scrape-Requests | `127` |
| `kamailio_exporter_failed_scrapes` | counter | Requests | Fehlgeschlagene Scrapes | `0` |

---

## 💾 Shared Memory (SHM) - **WICHTIG!**

Speicher der im RAM für Kamailio-Objekte reserviert ist.

| Metrik | Einheit | Bedeutung | Warnung | Beispiel |
|--------|---------|-----------|---------|----------|
| `kamailio_core_shmmem_total` | Bytes | **Total reservierter SHM** (in docker-compose: 128MB) | — | 134,217,728 = **128 MB** |
| `kamailio_core_shmmem_used` | Bytes | **Aktuell genutzter SHM** | >80% = Problem! | 2,596,320 = **2.5 MB** ✅ |
| `kamailio_core_shmmem_free` | Bytes | **Freier SHM** | <10% = Problem! | 131,321,408 = **125 MB** ✅ |
| `kamailio_core_shmmem_real_used` | Bytes | SHM inklusive Fragmentation | — | 2,985,888 = **2.9 MB** |
| `kamailio_core_shmmem_max_used` | Bytes | **Peak** (max. je genutzt) | — | 32,344,816 = **32 MB** |
| `kamailio_core_shmmem_fragments` | count | Speicher-Fragmentation | >1000 = schlecht | 303 ✅ |

### 🚨 SHM Probleme erkennen:

```
WARNUNG:
- used / total > 80%        → OOM-Risk!
- fragments > 1000          → Fragmentierung
- max_used stark gestiegen  → Memory-Leak?
```

### 📊 Healthy SHM:
```
✅ used: ~5-10% von total
✅ free: >90% von total
✅ max_used ≈ used (konstant, kein Anwachsen)
✅ fragments < 500
```

---

## 📞 Transaction Manager (TM) - **INVITES/CALLS**

Zählt alle SIP-Transaktionen (INVITE, BYE, etc.)

| Metrik | Typ | Bedeutung | Beispiel |
|--------|-----|-----------|----------|
| `kamailio_tm_stats_total_total` | counter | **Total erstelle Transactions** | `4999` |
| `kamailio_tm_stats_created_total` | counter | Neu erstellte (seit Start) | `4999` |
| `kamailio_tm_stats_current` | gauge | **Aktive Transactions jetzt** | `0` (nichts läuft) |
| `kamailio_tm_stats_waiting` | gauge | Auf Response wartend | `0` |
| `kamailio_tm_stats_freed_total` | counter | Abgebaut/abgeschlossen | `4999` |
| `kamailio_tm_stats_codes_total{code="2xx"}` | counter | Erfolgreiche Responses (200-299) | `0` |
| `kamailio_tm_stats_codes_total{code="4xx"}` | counter | Client-Fehler (400-499) | `4999` ⚠️ |
| `kamailio_tm_stats_codes_total{code="5xx"}` | counter | Server-Fehler (500-599) | `0` |
| `kamailio_tm_stats_rpl_generated_total` | counter | Von Kamailio generierte Responses | `9998` |
| `kamailio_tm_stats_rpl_sent_total` | counter | Versendete Responses | `9998` |
| `kamailio_tm_stats_rpl_received_total` | counter | Von Upstream empfangen | `0` |
| `kamailio_tm_stats_delayed_free_total` | counter | Delayed-Free Speicher | `0` |

### 📈 Last-Test Interpretation:

```
Ein erfolgreiches REGISTER + INVITE:
  • tm_stats_total_total: +1
  • tm_stats_created_total: +1
  • tm_stats_freed_total: +1
  • Wenn NICHT erfolgreich: code="4xx"

Medium-Test (2000 calls):
  • tm_stats_total_total sollte ~2000+ sein
  • Wenn code="4xx" hoch: Requests nicht verarbeitet
```

---

## 🚦 Stateless Module (SL) - **RESPONSES**

Zählt alle SIP-Response-Codes direkt vom Server.

| Metrik | Typ | Bedeutung | Gut? |
|--------|-----|-----------|------|
| `kamailio_sl_stats_codes_total{code="200"}` | counter | 200 OK - Erfolgreich | ✅ |
| `kamailio_sl_stats_codes_total{code="202"}` | counter | 202 Accepted | ✅ |
| `kamailio_sl_stats_codes_total{code="2xx"}` | counter | Alle 2xx (Erfolg) | ✅ |
| `kamailio_sl_stats_codes_total{code="3xx"}` | counter | Alle 3xx (Redirect) | ⚠️ |
| `kamailio_sl_stats_codes_total{code="400"}` | counter | 400 Bad Request | ❌ |
| `kamailio_sl_stats_codes_total{code="401"}` | counter | 401 Unauthorized | ❌ |
| `kamailio_sl_stats_codes_total{code="403"}` | counter | 403 Forbidden | ❌ |
| `kamailio_sl_stats_codes_total{code="404"}` | counter | 404 Not Found | ❌ |
| `kamailio_sl_stats_codes_total{code="407"}` | counter | 407 Proxy Auth Required | ❌ |
| `kamailio_sl_stats_codes_total{code="408"}` | counter | 408 Request Timeout | ❌ |
| `kamailio_sl_stats_codes_total{code="483"}` | counter | 483 Too Many Hops | ❌ |
| `kamailio_sl_stats_codes_total{code="4xx"}` | counter | Alle 4xx (Client-Fehler) | ❌ |
| `kamailio_sl_stats_codes_total{code="500"}` | counter | 500 Server Error | ❌ |
| `kamailio_sl_stats_codes_total{code="5xx"}` | counter | Alle 5xx (Server-Fehler) | ❌ |

### 🎯 Healthy Load-Test:

```
Medium-Test (2000 calls):
  ✅ code="200": ~2000 (alle REGISTERs erfolgreich)
  ✅ code="4xx": 0-100 (vereinzelte Fehler ok)
  ✅ code="5xx": 0 (keine Server-Fehler)
```

---

## 🌐 TCP Info - **CONNECTIONS**

TCP-Verbindungen (SIP über TCP/TLS).

| Metrik | Einheit | Bedeutung | Beispiel |
|--------|---------|-----------|----------|
| `kamailio_core_tcp_info_opened_connections` | count | **Aktiv offene TCP-Verbindungen** | `0` |
| `kamailio_core_tcp_info_opened_tls_connections` | count | TLS-Verbindungen | `0` |
| `kamailio_core_tcp_info_max_connections` | count | TCP-Limit | `2048` |
| `kamailio_core_tcp_info_max_tls_connections` | count | TLS-Limit | `2048` |
| `kamailio_core_tcp_info_readers` | count | TCP-Reader-Prozesse | `4` |
| `kamailio_core_tcp_info_write_queued_bytes` | Bytes | Gepufferte Daten zum Senden | `0` |

---

## 🔍 Exporter selbst

| Metrik | Bedeutung | Normal |
|--------|-----------|--------|
| `kamailio_exporter_total_scrapes` | Wie oft wurde Exporter gescraped | `100+` |
| `kamailio_exporter_failed_scrapes` | Scrape-Fehler | `0` ✅ |

---

## 📋 Checkliste: Ist alles ok?

### ✅ Nach dem Start (Idle):

```
kamailio_up: 1
core.shmmem_used: 1-5 MB
tm_stats_current: 0
sl_stats{200}: 0
tcp_opened_connections: 0
```

### ✅ Während Light-Test (50 Calls):

```
tm_stats_created_total: ~50
tm_stats_current: 0-5 (parallel)
sl_stats{200}: ~50
core.shmmem_used: 5-10 MB (max +5MB)
```

### ✅ Während Medium-Test (2000 Calls):

```
tm_stats_created_total: ~2000
tm_stats_current: 0-50 (parallel)
sl_stats{200}: ~2000
core.shmmem_used: 10-20 MB
core.shmmem_max_used: <50 MB (noch weit weg von 128MB)
```

### ⚠️ PROBLEME:

```
🚨 core.shmmem_used > 100 MB          → Out of Memory!
🚨 tm_stats_codes{4xx} > 10% requests → Config-Problem
🚨 tm_stats{current} bleibt hoch      → Transactions hängen
🚨 tcp_opened_connections > 100       → Zu viele Verbindungen
🚨 exporter_failed_scrapes > 0        → Kamailio nicht erreichbar
```

---

## 💡 PromQL Queries (für Prometheus/Grafana)

### Rate-Metriken (Transaktionen/Sekunde):

```promql
# Transactions pro Sekunde
rate(kamailio_tm_stats_created_total[1m])

# Erfolgreiche Responses pro Sekunde
rate(kamailio_sl_stats_codes_total{code="200"}[1m])

# Fehler pro Sekunde
rate(kamailio_sl_stats_codes_total{code="4xx"}[1m])
```

### Memory-Metriken:

```promql
# Speicherverfügbarkeit
kamailio_core_shmmem_free / kamailio_core_shmmem_total * 100

# Peak Memory im Zeitfenster
max_over_time(kamailio_core_shmmem_used[1h])
```

### Fehlerrate:

```promql
# % 4xx Fehler
rate(kamailio_sl_stats_codes_total{code="4xx"}[1m]) / 
rate(kamailio_sl_stats_codes_total[1m]) * 100
```

---

## 📚 Weitere Infos

- **Kamailio Docs**: https://kamailio.org/docs/
- **SIP Response Codes**: RFC 3261 Section 21
- **Exporter**: https://github.com/florentchauveau/kamailio_exporter
