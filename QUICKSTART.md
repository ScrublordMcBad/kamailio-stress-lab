# Quick Start

## Voraussetzungen
- Docker + Docker Compose Plugin installiert (`docker compose version`)
- Internetzugang beim ersten Start (der Exporter wird live aus GitHub gebaut)
- Port `5060` (UDP+TCP), `9090`, `9494`, `3000`, `8080` frei auf dem Host
  - `8080` ist für den Load Controller (optional, nur wenn du Last-Tests triggerst)

## Starten

```bash
docker compose up -d --build
```

Der `--build` ist beim ersten Mal wichtig, weil `kamailio_exporter` und 
`load_controller` aus dem lokalen Dockerfile gebaut werden.

## Läuft alles?

```bash
# 1. Container-Status
docker compose ps

# 2. Kamailio-Log auf Fehler prüfen
docker compose logs kamailio --tail=50

# 3. Exporter erreicht Kamailio per BINRPC?
curl -s http://localhost:9494/metrics | grep kamailio_up
# erwartet: kamailio_up 1  (0 = Verbindung zu Kamailio klappt nicht)

# 4. Zieht Prometheus die Metriken?
# Browser: http://localhost:9090/targets
# -> Zeile "kamailio_exporter" sollte grün/"UP" sein
```

## Dashboard + Load Tests

### Grafana Dashboard öffnen
1. Browser: `http://localhost:3000`
2. Login: `admin` / `admin` (Grafana fragt danach nach einem neuen Passwort)
3. Dashboards → Ordner **Kamailio** → **Kamailio (kamailio_exporter)**
   (liegt automatisch da, kein Import nötig)

### Load-Tests triggern (Web UI)
1. Browser: `http://localhost:8080` (Load Controller)
2. Profil wählen (**Light** / **Medium** / **Heavy**)
3. Button klicken → Test startet sofort
4. Metriken in Grafana beobachten (rechts)
5. [Detaillierte Anleitung](LOAD_CONTROLLER_README.md)

## Stoppen / Aufräumen

```bash
# Container stoppen, Daten (Prometheus-TSDB, Grafana-DB) bleiben erhalten
docker compose down

# Alles inkl. Volumes löschen (sauberer Neustart)
docker compose down -v
```

## Wenn was klemmt

| Symptom | Wahrscheinliche Ursache | Erster Check |
|---|---|---|
| `kamailio_up 0` | Exporter kommt nicht per BINRPC an Kamailio ran | `docker compose logs kamailio` – lädt `ctl.so`? bindet auf `2049`? |
| Exporter-Container crasht sofort | Build aus GitHub fehlgeschlagen (kein Internet, GitHub down) | `docker compose logs kamailio_exporter` |
| Port `5060` schon belegt | Läuft bei dir schon ein anderer SIP-Dienst/Router auf 5060 | Host-Port in `docker-compose.yml` unter `kamailio.ports` ändern, z. B. `5061:5060/udp` |
| Grafana zeigt keine Daten | Prometheus-Target down, oder Zeitraum falsch | `http://localhost:9090/targets` prüfen, Dashboard-Zeitraum auf "Last 15 min" stellen |
| Load Controller UI nicht erreichbar | Container läuft nicht oder Port 8080 belegt | `docker compose ps load-controller`, `docker compose logs load-controller` |
| Load Tests starten nicht | sip_client kann sich nicht mit Kamailio verbinden | `docker compose logs load_controller` – Fehler im Log, Netzwerk-Verbindung prüfen |
