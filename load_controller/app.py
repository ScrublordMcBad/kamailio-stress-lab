#!/usr/bin/env python3
import os
import subprocess
import json
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Grafana Config
GRAFANA_URL = "http://grafana:3000"
GRAFANA_DASHBOARDS = {
    "test-analysis": "kamailio-test-analysis"
}

# Load-Test Profile
PROFILES = {
    "light": {
        "name": "Light Load",
        "description": "Baseline test",
        "rate": 5,
        "parallel": 10,
        "calls": 500,
    },
    "medium": {
        "name": "Medium Load",
        "description": "Normal production load",
        "rate": 20,
        "parallel": 50,
        "calls": 2000,
    },
    "heavy": {
        "name": "Heavy Load",
        "description": "Stress & peak load test",
        "rate": 50,
        "parallel": 100,
        "calls": 5000,
    },
}

# Track laufende Tests
active_tests = {}


@app.route("/")
def index():
    return render_template("index.html", profiles=PROFILES)


@app.route("/api/profiles", methods=["GET"])
def get_profiles():
    return jsonify(PROFILES)


@app.route("/api/status", methods=["GET"])
def get_status():
    from datetime import datetime as dt

    # Filter out non-JSON-serializable objects (process, thread)
    safe_tests = []
    for test in active_tests.values():
        safe_test = {k: v for k, v in test.items() if k not in ['process', 'processes']}

        # Use actual progress if available, otherwise estimate from time
        if "progress" not in safe_test and test["status"] == "running":
            started = dt.fromisoformat(test["started"])
            now = dt.now()
            elapsed = (now - started).total_seconds()

            # Estimate total duration
            if "total_calls" in test and "rate" in test and test["rate"] > 0:
                # Preset/Custom: duration = calls / rate * 1.1
                total_duration = (test["total_calls"] / test["rate"]) * 1.1
            elif "duration" in test:
                # Live Test: duration in minutes * 60
                total_duration = test["duration"] * 60
            else:
                total_duration = 1

            progress = min(100, int((elapsed / total_duration) * 100))
            safe_test["progress"] = progress
        elif test["status"] != "running":
            safe_test["progress"] = 100

        safe_tests.append(safe_test)

    return jsonify({
        "active_tests": len(active_tests),
        "tests": safe_tests
    })


@app.route("/api/run/<profile>", methods=["POST"])
def run_test(profile):
    # Allow custom profile from POST data, or presets
    data = request.get_json(silent=True) or {}
    encrypted = bool(data.get("encrypted", False))

    if profile == "custom":
        cfg = {
            "name": "Custom Load",
            "rate": int(data.get("rate", 10)),
            "parallel": int(data.get("parallel", 20)),
            "calls": int(data.get("calls", 500)),
        }
        profile_key = "custom"
    else:
        if profile not in PROFILES:
            return jsonify({"error": f"Unknown profile: {profile}"}), 400
        cfg = PROFILES[profile].copy()
        profile_key = profile

    test_id = f"{profile_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Python SIP Load Client Command
    mode = "tls" if encrypted else "udp"
    cmd = [
        "python3", "/app/sip_client.py",
        "kamailio",  # Kamailio hostname (resolves in docker network)
        str(cfg["rate"]),
        str(cfg["parallel"]),
        str(cfg["calls"]),
        mode,
    ]

    try:
        # Starte SIP Client Prozess im Hintergrund
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        started_time = datetime.now().isoformat()
        active_tests[test_id] = {
            "id": test_id,
            "profile": profile_key,
            "name": cfg["name"],
            "started": started_time,
            "rate": cfg["rate"],
            "parallel": cfg["parallel"],
            "total_calls": cfg["calls"],
            "status": "running",
            "encrypted": encrypted,
            "pid": proc.pid,
            "process": proc,
        }

        # Create Grafana annotation for test start
        create_grafana_annotation(test_id, cfg["name"], started_time, "started")

        # Starte Thread zum Monitoren des Prozesses
        def monitor_process():
            try:
                print(f"📍 Monitor started for {test_id}", flush=True)

                # Read stdout line-by-line to capture progress
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.rstrip()

                    # Parse PROGRESS: sent/total:pct
                    if line.startswith("PROGRESS:"):
                        try:
                            parts = line.split(":")
                            sent = int(parts[1].split("/")[0])
                            total = int(parts[1].split("/")[1])
                            pct = int(parts[2])
                            if test_id in active_tests:
                                active_tests[test_id]["progress"] = pct
                                active_tests[test_id]["calls_sent"] = sent
                        except:
                            pass
                    else:
                        print(line, flush=True)

                # Wait for process to finish
                return_code = proc.wait(timeout=600)
                print(f"✅ Process ended with code {return_code} for {test_id}", flush=True)

                # Mark as completed
                if test_id in active_tests:
                    active_tests[test_id]["status"] = "completed"
                    active_tests[test_id]["ended"] = datetime.now().isoformat()

                    # Create Grafana annotation for test end
                    create_grafana_annotation(test_id, cfg["name"], started_time, "completed")
                    print(f"✅ Annotation for completion created", flush=True)
                    print(f"📍 Monitor finished for {test_id}", flush=True)
                else:
                    print(f"⚠️  Test {test_id} not in active_tests dict!", flush=True)
            except Exception as e:
                print(f"❌ Monitor error for {test_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()

        import threading
        monitor_thread = threading.Thread(target=monitor_process, daemon=False, name=f"monitor-{test_id}")
        monitor_thread.start()

        # Store thread reference to prevent garbage collection
        if not hasattr(app, 'monitor_threads'):
            app.monitor_threads = {}
        app.monitor_threads[test_id] = monitor_thread

        return jsonify({
            "success": True,
            "test_id": test_id,
            "message": f"Started {cfg['name']} test"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/run/live", methods=["POST"])
def run_live_test():
    data = request.get_json()
    users = int(data.get("users", 40000))
    duration_minutes = int(data.get("duration", 10))
    pattern = data.get("pattern", "ramp-up")
    encrypted = bool(data.get("encrypted", False))

    test_id = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Start live test in background thread
    import threading
    def run_live():
        try:
            started_time = datetime.now().isoformat()
            active_tests[test_id] = {
                "id": test_id,
                "profile": "live",
                "name": f"Live Test ({users:,} users)",
                "started": started_time,
                "rate": 0,  # Will vary
                "parallel": int(users * 0.1),
                "total_calls": 0,  # Will vary
                "status": "running",
                "encrypted": encrypted,
                "pid": None,
                "pattern": pattern,
                "users": users,
                "duration": duration_minutes,
                "processes": [],
            }

            # Create start annotation
            create_grafana_annotation(test_id, active_tests[test_id]["name"], started_time, "started")

            # Calculate phases (1 phase per minute)
            phases = duration_minutes
            calls_per_user_per_min = 4  # Realistic assumption
            total_calls = users * calls_per_user_per_min * duration_minutes

            print(f"🎬 Live test started: {users:,} users, {duration_minutes} min, pattern={pattern}", flush=True)

            for phase in range(1, phases + 1):
                # Calculate rate for this phase based on pattern
                if pattern == "ramp-up":
                    # Linear ramp from 10% to 100%
                    progress = phase / phases
                    rate_factor = 0.1 + (progress * 0.9)  # 10% to 100%
                elif pattern == "peak":
                    # Ramp-up, peak, ramp-down
                    if phase <= phases * 0.3:  # First 30%
                        rate_factor = 0.1 + (phase / (phases * 0.3)) * 0.4  # 10% to 50%
                    elif phase <= phases * 0.7:  # Middle 40%
                        rate_factor = 1.0  # Full peak
                    else:  # Last 30%
                        rate_factor = 1.0 - ((phase - phases * 0.7) / (phases * 0.3)) * 0.5  # 100% to 50%
                else:  # sawtooth
                    # Oscillating pattern
                    rate_factor = 0.4 + 0.5 * (0.5 + 0.5 * ((phase % 2) - 0.5))  # Oscillate 40-90%

                # Calculate calls and rate for this phase
                phase_calls = int(total_calls / phases)
                phase_rate = max(5, int((users * calls_per_user_per_min * rate_factor) / 60))
                phase_parallel = int(users * rate_factor * 0.1)  # 10% concurrent

                print(f"📍 Phase {phase}/{phases}: {rate_factor*100:.0f}% load, {phase_rate} calls/sec", flush=True)

                # Start process for this phase
                mode = "tls" if encrypted else "udp"
                cmd = [
                    "python3", "/app/sip_client.py",
                    "kamailio",
                    str(phase_rate),
                    str(phase_parallel),
                    str(phase_calls),
                    mode,
                ]

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                active_tests[test_id]["processes"].append(proc)

                # Wait for process to complete
                stdout, stderr = proc.communicate(timeout=600)
                if proc.returncode != 0:
                    print(f"⚠️ Phase {phase} ended with code {proc.returncode}", flush=True)

            # All phases done
            if test_id in active_tests:
                active_tests[test_id]["status"] = "completed"
                active_tests[test_id]["ended"] = datetime.now().isoformat()
                create_grafana_annotation(test_id, active_tests[test_id]["name"], started_time, "completed")
                print(f"✅ Live test completed: {test_id}", flush=True)

        except Exception as e:
            print(f"❌ Live test error for {test_id}: {e}", flush=True)
            if test_id in active_tests:
                active_tests[test_id]["status"] = "failed"
            import traceback
            traceback.print_exc()

    thread = threading.Thread(target=run_live, daemon=False, name=f"live-{test_id}")
    thread.start()

    if not hasattr(app, 'monitor_threads'):
        app.monitor_threads = {}
    app.monitor_threads[test_id] = thread

    return jsonify({
        "success": True,
        "test_id": test_id,
        "message": f"Started Live Test with {users:,} users for {duration_minutes} minutes"
    })


@app.route("/api/stop/<test_id>", methods=["POST"])
def stop_test(test_id):
    if test_id not in active_tests:
        return jsonify({"error": "Test not found"}), 404

    test = active_tests[test_id]
    try:
        # Stop the SIP client process
        if "process" in test and test["process"]:
            test["process"].terminate()
            test["process"].wait(timeout=3)

        test["status"] = "stopped"
        test["ended"] = datetime.now().isoformat()

        # Create Grafana annotation for test stop
        create_grafana_annotation(test_id, test["name"], test["started"], "stopped")
        print(f"🛑 Test stopped by user: {test_id}", flush=True)

        return jsonify({"success": True, "message": "Test stopped"})
    except Exception as e:
        print(f"❌ Error stopping test {test_id}: {e}", flush=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
def clear_history():
    active_tests.clear()
    return jsonify({"success": True})


@app.route("/api/estimate-duration", methods=["POST"])
def estimate_duration():
    """Calculate estimated test duration"""
    data = request.get_json()
    rate = int(data.get("rate", 1))
    calls = int(data.get("calls", 100))

    # Simplified: duration = calls / rate
    # In reality slightly longer due to overhead, so add 10%
    duration_sec = (calls / rate) * 1.1

    return jsonify({
        "duration_seconds": int(duration_sec),
        "duration_formatted": format_duration(duration_sec)
    })


def format_duration(seconds):
    """Format duration as HH:MM:SS or MM:SS"""
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    elif secs < 3600:
        mins = secs // 60
        secs = secs % 60
        return f"{mins}m {secs}s"
    else:
        hours = secs // 3600
        mins = (secs % 3600) // 60
        return f"{hours}h {mins}m"


def create_grafana_annotation(test_id, test_name, started, status):
    """Create annotation in Grafana for test run"""
    try:
        timestamp = int(datetime.fromisoformat(started).timestamp() * 1000)

        # Get encryption status for badge
        encrypted = False
        if test_id in active_tests:
            encrypted = active_tests[test_id].get("encrypted", False)

        badge = "🔒" if encrypted else "🔓"
        encryption_tag = "encrypted" if encrypted else "unencrypted"

        payload = {
            "dashboardUID": GRAFANA_DASHBOARDS["test-analysis"],
            "text": f"{badge} {test_name} - {status.upper()}",
            "tags": ["test-run", status, encryption_tag],
            "time": timestamp,
            "isRegion": False
        }

        # Try to create annotation with basic auth (optional - don't fail if Grafana unreachable)
        response = requests.post(
            f"{GRAFANA_URL}/api/annotations",
            json=payload,
            timeout=2,
            auth=("admin", "admin"),
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print(f"✅ Annotation created: {test_name} ({status})", flush=True)
        else:
            print(f"⚠️ Annotation failed ({response.status_code}): {response.text[:80]}", flush=True)

    except requests.exceptions.ConnectionError:
        print(f"ℹ️ Grafana unreachable - annotations skipped", flush=True)
    except Exception as e:
        print(f"⚠️ Annotation error: {str(e)[:80]}", flush=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
