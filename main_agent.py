import argparse
import threading
import time
import logging
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

agents = {}
agents_lock = threading.Lock()

STALE_AFTER_SECONDS = 15

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
            "disk": data.get("disk"),
            "last_action": data.get("last_action", "-"),
            "last_seen": time.time(),
            "online": True,
        }
    if was_offline:
        logging.info(f"Sub-agent '{agent_id}' is back online.")
    return jsonify({"ok": True})