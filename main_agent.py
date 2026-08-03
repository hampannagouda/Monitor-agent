#!/usr/bin/env python3
"""
Main Agent
----------
Monitors multiple sub-agents (instances of monitor_agent.py running on
different machines/folders). Each sub-agent periodically POSTs a status
report to this main agent. This agent:

  - Tracks every sub-agent it has heard from (by agent_id)
  - Shows a live dashboard of their CPU / disk / last action
  - Flags a sub-agent as OFFLINE if it hasn't reported in --stale-after seconds

USAGE:
    pip install flask
    python main_agent.py                        # listens on 0.0.0.0:5000
    python main_agent.py --port 8080 --stale-after 20

Then open http://<this-machine-ip>:5000/dashboard in a browser.
"""

import argparse
import threading
import time
import logging
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# In-memory store of sub-agent status: agent_id -> latest report dict
agents = {}
agents_lock = threading.Lock()

STALE_AFTER_SECONDS = 15  # set from CLI arg in main()


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("main_agent.log"),
            logging.StreamHandler(),
        ],
    )


@app.route("/report", methods=["POST"])
def report():
    """Sub-agents call this endpoint to check in."""
    data = request.get_json(force=True, silent=True)
    if not data or "agent_id" not in data:
        return jsonify({"error": "agent_id is required"}), 400

    agent_id = data["agent_id"]
    with agents_lock:
        was_offline = agents.get(agent_id, {}).get("online") is False
        agents[agent_id] = {
            "agent_id": agent_id,
            "hostname": data.get("hostname", "unknown"),
            "cpu": data.get("cpu"),
            "ram": data.get("ram"),
            "disk": data.get("disk"),
            "last_action": data.get("last_action", "-"),
            "last_seen": time.time(),
            "online": True,
        }
    if was_offline:
        logging.info(f"Sub-agent '{agent_id}' is back ONLINE.")
    return jsonify({"ok": True})


def _snapshot():
    with agents_lock:
        now = time.time()
        rows = []
        for a in agents.values():
            row = dict(a)
            row["seconds_since_report"] = round(now - a["last_seen"], 1)
            rows.append(row)
    rows.sort(key=lambda x: x["agent_id"])
    return rows


@app.route("/status", methods=["GET"])
def status():
    """Machine-readable status of every known sub-agent."""
    return jsonify(_snapshot())


DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <title>Sub-Agent Dashboard</title>
  <meta http-equiv="refresh" content="5">
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
    h1 { color: #333; }
    table { border-collapse: collapse; width: 100%; background: white; }
    th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
    th { background: #333; color: white; }
    .online { color: green; font-weight: bold; }
    .offline { color: red; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Sub-Agent Dashboard</h1>
  <p>Auto-refreshes every 5s. A sub-agent is marked OFFLINE after {{ stale_after }}s of silence.</p>
  <table>
    <tr>
      <th>Agent ID</th><th>Hostname</th><th>CPU %</th><th>RAM %</th><th>Disk %</th>
      <th>Last Action</th><th>Last Seen (s ago)</th><th>Status</th>
    </tr>
    {% for a in agents %}
    <tr>
      <td>{{ a.agent_id }}</td>
      <td>{{ a.hostname }}</td>
      <td>{{ a.cpu }}</td>
      <td>{{ a.ram }}</td>
      <td>{{ a.disk }}</td>
      <td>{{ a.last_action }}</td>
      <td>{{ a.seconds_since_report }}</td>
      <td class="{{ 'online' if a.online else 'offline' }}">
        {{ 'ONLINE' if a.online else 'OFFLINE' }}
      </td>
    </tr>
    {% endfor %}
    {% if not agents %}
    <tr><td colspan="7">No sub-agents have reported in yet.</td></tr>
    {% endif %}
  </table>
</body>
</html>
"""


@app.route("/", methods=["GET"])
@app.route("/dashboard", methods=["GET"])
def dashboard():
    return render_template_string(DASHBOARD_HTML, agents=_snapshot(), stale_after=STALE_AFTER_SECONDS)


def watchdog_loop():
    """Background thread: flag sub-agents OFFLINE if they've gone quiet too long."""
    while True:
        time.sleep(5)
        now = time.time()
        with agents_lock:
            for agent_id, a in agents.items():
                if a["online"] and (now - a["last_seen"] > STALE_AFTER_SECONDS):
                    a["online"] = False
                    logging.warning(
                        f"Sub-agent '{agent_id}' ({a['hostname']}) went OFFLINE "
                        f"(no report in over {STALE_AFTER_SECONDS}s)."
                    )


def main():
    global STALE_AFTER_SECONDS

    parser = argparse.ArgumentParser(description="Main agent - monitors sub-agents over the network")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
    parser.add_argument("--stale-after", type=int, default=15,
                         help="Seconds of silence before marking a sub-agent OFFLINE (default: 15)")
    args = parser.parse_args()
    STALE_AFTER_SECONDS = args.stale_after

    setup_logging()
    logging.info(f"Main agent starting on port {args.port}. Stale threshold: {STALE_AFTER_SECONDS}s")
    logging.info(f"Dashboard:   http://<this-machine-ip>:{args.port}/dashboard")
    logging.info(f"JSON status: http://<this-machine-ip>:{args.port}/status")

    threading.Thread(target=watchdog_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()