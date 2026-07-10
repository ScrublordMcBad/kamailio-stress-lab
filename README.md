# Kamailio + Prometheus + Grafana - minimaler Test-Stack

Mit integriertem **Web-basierten Load Controller** zum Triggern von SIP-Last-Tests.

## Warum dieser Stack so aussieht (Entscheidungen + Begründung)

| Entscheidung | Optionen geprüft | Wahl | Begründung |
|---|---|---|---|
| Kamailio-Image | eigenes Dockerfile vs. offizielles Image | `ghcr.io/kamailio/kamailio:5.8.8-bookworm` | Offizielles Image (kamailio/kamailio-docker Repo), Docker Hub wurde 2023 wegen Storage-Limits abgekündigt, Registry ist seither ghcr.io. Version 5.8.x gewählt, weil das zur 5.8-Doku passt, mit der du schon gearbeitet hast (nicht 6.x, das hätte teils andere Modulnamen, s.u.). |
| Exporter-Bezug | fertiges Docker-Hub-Image vs. Build aus Source | Build direkt aus `github.com/florentchauveau/kamailio_exporter.git` | Es gibt mehrere Forks mit Docker-Images (florentchauveau, pascomnet, angarium-cloud, talkdesk ...), aber keinen eindeutig verifizierbaren, gepflegten Tag-Namen ohne weitere Prüfung. Das Original-Repo hat ein schlankes, aktuelles Dockerfile (Go-Build, `scratch`-Image) - das baut Docker beim ersten `up` selbst, ohne dass ich einen möglicherweise veralteten Fremd-Tag raten muss. |
| Kamailio <-> Exporter Verbindung | Unix-Socket (geteiltes Volume) vs. TCP | TCP (`tcp:0.0.0.0:2049`) | Zwei getrennte Container = zwei Netzwerk-Namespaces. Ein Unix-Socket ginge nur über ein gemeinsames Volume, TCP ist im Docker-Netz der geradlinigere Weg und ist von den Exporter-Maintainern selbst als Standardmuster für "Exporter als Sidecar" dokumentiert. |
| Grafana-Dashboard | fertiges Community-Dashboard (grafana.com) importieren | selbst gebaut, gegen die Exporter-Metriknamen | Ich habe gezielt gesucht. Das einzige öffentlich auffindbare "Kamailio"-Dashboard (lehisnoe/grafana-dashboards) ist gegen **InfluxDB/Telegraf** gebaut, nicht gegen Prometheus - andere Feldnamen, anderes Datenmodell, nicht kompatibel. Eher als ein fremdes Dashboard zu nehmen, das nicht zu unseren Metriken passt, habe ich ein kleines Dashboard direkt gegen die tatsächlichen `kamailio_exporter`-Metriknamen gebaut (siehe unten, "Was tatsächlich verifiziert wurde"). |
| Load-Test Controller | CLI-only vs. Web UI | Flask Web Service mit Python SIP Client | Last-Tests gezielt triggern (on-demand). Web UI mit 3 Modi: Presets (Light/Medium/Heavy), Custom, Live Test mit dynamischen Patterns. REST API für Automation. Grafana Annotations für Test-Markierungen. |

## Was tatsächlich verifiziert wurde (und wie)

Nach der Kritik im Chat vorher galt hier: nichts aus dem Gedächtnis, alles nachgeschlagen.

- **Kamailio-Image/Tags**: geprüft über `github.com/kamailio/kamailio-docker` (Entrypoint, `SHM_MEMORY`/`PKG_MEMORY`-Env-Vars, `VOLUME /etc/kamailio`) und die Package-Versionsliste auf GitHub (bestätigt: `5.8.8-bookworm` existiert).
- **Exporter-Verhalten**: README von `florentchauveau/kamailio_exporter` (Flags, Default-Methoden, Metriknamen wie `kamailio_core_shmmem_*`) sowie das tatsächliche `Dockerfile` im Repo.
- **kamailio.cfg-Inhalt**: Struktur und exakte Funktionsnamen (`sanity_check("17895","7")`, `mf_process_maxfwd_header("10")`, `send_reply_error()`, `t_relay()`, `save("location")`, `lookup("location")`, `nat_uac_test("19")` etc.) 1:1 aus dem offiziellen `etc/kamailio.cfg` im Kamailio-Quellrepo übernommen und dann gekürzt (kein DB-Backend, kein TLS, kein Presence/PSTN/RTP-Relay) - nicht frei erfunden oder aus altem Trainingswissen rekonstruiert.
- **Dashboard**: nur Metriknamen verwendet, die wörtlich im Exporter-README als Beispielausgabe auftauchen.

## Was NICHT getestet wurde (wichtig!)

Ich habe in dieser Umgebung keinen Docker-Daemon zur Verfügung - ich konnte also:
- ✅ JSON/YAML aller Dateien auf Syntax validieren (automatisiert geprüft, ist ok)
- ✅ Klammern-/Anführungszeichen-Balance in der `kamailio.cfg` grob geprüft
- ❌ **NICHT** `docker compose up` tatsächlich laufen lassen
- ❌ **NICHT** verifizieren, dass Kamailio mit dieser Config tatsächlich fehlerfrei hochfährt (`kamailio -c` Config-Check)
- ❌ **NICHT** verifizieren, dass der Exporter sich per BINRPC erfolgreich verbindet

Sprich: strukturell und inhaltlich auf echte Quellen gestützt, aber **ein erster Testlauf bei dir ist nötig**, bevor das irgendwo ernsthaft verwendet wird.

## Setup starten

```bash
docker compose up -d --build
```

### Services & Ports

| Service | Port | Zweck |
|---------|------|-------|
| **Kamailio** | `5060/udp`, `5060/tcp` | SIP Server |
| **kamailio_exporter** | `9494` | Prometheus Metrics |
| **Prometheus** | `9090` | Zeitreihendatenbank |
| **Grafana** | `3000` | Dashboards & Visualisierung |
| **load-controller** | `8080` | Web UI für Load-Tests ⭐ |

### Erste Schritte nach dem Start

1. **Dashboard öffnen**: http://localhost:3000 (admin/admin)
   - Dashboards → Kamailio Ordner → Kamailio (kamailio_exporter)
   
2. **Load-Tests starten**: http://localhost:8080
   - Profil wählen → Klick → Test läuft
   - [Anleitung](LOAD_CONTROLLER_README.md)
   
3. **Metriken live überwachen**:
   ```bash
   curl -s http://localhost:9494/metrics | grep -E 'tm_|sl_|shmmem'
   ```

## Troubleshooting

```bash
# 1. Alle Container laufen?
docker compose ps

# 2. Kamailio Logs (auf Fehler prüfen)
docker compose logs kamailio --tail=50

# 3. Exporter verbunden?
curl -s http://localhost:9494/metrics | grep kamailio_up
# erwartet: kamailio_up 1 (0 = BINRPC-Problem)

# 4. Prometheus scrapet Metriken?
# Browser: http://localhost:9090/targets
# → kamailio_exporter sollte grün/"UP" sein

# 5. Load Controller online?
docker compose logs load_controller
```

Falls `kamailio_up` bei 0 steht: meist BINRPC-Verbindungsproblem - prüfen, ob im Kamailio-Log der ctl-Modul-Load und der TCP-Bind auf `2049` sauber durchläuft.

## Bekannte Einschränkungen / bewusst weggelassen

**Kamailio-Konfiguration:**
- Kein DB-Backend (MySQL) → keine persistente Registrierung über Neustarts hinaus, keine SIP-Auth
  - **Nur für Labortests geeignet, nicht Internet-exposed**
- Kein TLS/WSS
- Kein RTPEngine/RTPProxy → Media-Relay/NAT-Traversal nur teilweise abgedeckt
- `dialog`-Modul nicht geladen → `dlg_stats_active` nicht verfügbar (für `core.shmmem` irrelevant, aber nachrüstbar)
- `xhttp_prom` **nicht** aktiv → dieser Stack nutzt ausschließlich externen BINRPC-Exporter

**Load-Test Controller:**
- Python sip_client.py läuft im gleichen Docker-Netzwerk (Loopback-Szenario)
- 3 Test-Modi: Presets (Light/Medium/Heavy), Custom (freie Parameter), Live Test (dynamisch skalierbar)
- Testläufe werden automatisch in Grafana annotiert (Start/End-Marker)
- Vordefinierte Profile (Light/Medium/Heavy), neue Profiles leicht hinzufügbar

## Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│              Docker Compose Stack                           │
├──────────────────────┬──────────────────────────────────────┤
│  Kamailio (5060)     │  Load-Controller (5000)               │
│  SIP Server          │  Flask UI + SIPp Launcher            │
│                      │  - Light / Medium / Heavy Profiles    │
│  - registrar         │  - On-Demand Test Trigger            │
│  - tm (transactions) │  - Live Status Monitoring             │
│  - sl (stateless)    │                                       │
│  - core (shmmem)     │  ┌─ SIPp (ephemeral)                 │
│  - ctl (BINRPC)      │  │  Started per Test                 │
│                      │  └─ register_and_call.xml            │
├──────────────────────┴──────────────────────────────────────┤
│  kamailio_exporter (9494)                                    │
│  Scrapes Kamailio via BINRPC/2049                            │
│  → Prometheus Metrics                                        │
├────────────────────────────────────────────────────────────┤
│  Prometheus (9090)  │  Grafana (3000)                        │
│  TSDB               │  Dashboards (Kamailio Stats)           │
└────────────────────────────────────────────────────────────┘
```

## Dokumentation

- [Quick Start](QUICKSTART.md) – Setup & erste Schritte
- [Load Test Guide](LOAD_TEST_GUIDE.md) – Load-Test Optionen (Web UI + CLI)
- [Load Controller README](LOAD_CONTROLLER_README.md) – Detaillierte UI-Anleitung
- **[Metrics Reference](METRICS_REFERENCE.md)** – Alle Prometheus Metriken erklärt 📊
- **[Dashboards Guide](DASHBOARDS_GUIDE.md)** – 3 vollständige Grafana Dashboards 📈

## Quellen

- https://github.com/kamailio/kamailio-docker
- https://github.com/kamailio/kamailio/blob/master/etc/kamailio.cfg
- https://github.com/florentchauveau/kamailio_exporter
- https://github.com/florentchauveau/go-kamailio-binrpc
