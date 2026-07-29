#!/usr/bin/env python3
"""
Simple System Monitor Agent
----------------------------
Watches CPU, RAM, and disk usage. If CPU or RAM usage crosses its
threshold, it finds the process using the most of that resource and
kills it — unless that process is on the "protected" list.

USAGE:
    python monitor_agent.py                     # dry-run, just logs
    python monitor_agent.py --live               # actually kills processes
    python monitor_agent.py --cpu-threshold 80 --ram-threshold 85 --interval 5
"""

import psutil
import time
import argparse
import logging
import socket
import json
import urllib.request
from datetime import datetime

# ---------- Configuration ----------

# Processes that should NEVER be killed, even if they spike.
# Add your own OS-critical or important app names here (lowercase).
PROTECTED_PROCESSES = {
    "systemd", "kernel_task", "launchd", "init",
    "explorer.exe", "winlogon.exe", "csrss.exe", "services.exe",
    "python", "python3",              # don't let it kill itself
    "sshd", "bash", "zsh", "cmd.exe", "powershell.exe",
}

COOLDOWN_SECONDS = 30   # wait this long after a kill before killing again


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("monitor_agent.log"),
            logging.StreamHandler(),
        ],
    )


def report_to_main_agent(report_url, agent_id, cpu, ram, disk, last_action):
    """POST a short status update to the main agent. Never blocks the loop for long,
    and never crashes the sub-agent if the main agent / network is unreachable."""
    if not report_url:
        return
    payload = json.dumps({
        "agent_id": agent_id,
        "hostname": socket.gethostname(),
        "cpu": round(cpu, 1),
        "ram": round(ram, 1),
        "disk": round(disk, 1),
        "last_action": last_action,
    }).encode("utf-8")

    req = urllib.request.Request(
        report_url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        logging.warning(f"Could not reach main agent at {report_url}: {e}")


def get_disk_usage(path="/"):
    usage = psutil.disk_usage(path)
    return usage.percent


def get_ram_usage():
    return psutil.virtual_memory().percent


def get_top_cpu_process(exclude_pid=None):
    """Return the process (as psutil.Process) using the most CPU right now."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            if p.info["pid"] == exclude_pid:
                continue
            procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # cpu_percent needs a warm-up call to be meaningful
    for p in procs:
        try:
            p.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    time.sleep(0.5)  # short sampling window

    best = None
    best_cpu = -1
    for p in procs:
        try:
            cpu = p.cpu_percent(interval=None)
            if cpu > best_cpu:
                best_cpu = cpu
                best = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return best, best_cpu


def get_top_ram_process(exclude_pid=None):
    """Return the process using the most RAM right now, as (proc, percent)."""
    best = None
    best_ram = -1
    for p in psutil.process_iter(["pid", "memory_percent"]):
        try:
            if p.info["pid"] == exclude_pid:
                continue
            ram = p.info["memory_percent"]
            if ram is not None and ram > best_ram:
                best_ram = ram
                best = p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return best, best_ram


def is_protected(proc):
    try:
        name = proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return True  # if we can't even inspect it, don't touch it
    return name in PROTECTED_PROCESSES


def kill_process(proc, dry_run):
    try:
        name = proc.name()
        pid = proc.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return

    if dry_run:
        logging.warning(f"[DRY RUN] Would kill process: {name} (PID {pid})")
        return

    try:
        proc.terminate()   # ask nicely first (SIGTERM)
        proc.wait(timeout=3)
        logging.warning(f"Killed process: {name} (PID {pid})")
    except psutil.TimeoutExpired:
        proc.kill()        # force kill (SIGKILL) if it didn't respond
        logging.warning(f"Force-killed process: {name} (PID {pid})")
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logging.error(f"Could not kill {name} (PID {pid}): {e}")


def main():
    parser = argparse.ArgumentParser(description="Simple CPU/Disk monitor agent")
    parser.add_argument("--cpu-threshold", type=float, default=85.0,
                         help="CPU usage %% that triggers action (default: 85)")
    parser.add_argument("--ram-threshold", type=float, default=85.0,
                         help="RAM usage %% that triggers action (default: 85)")
    parser.add_argument("--disk-threshold", type=float, default=90.0,
                         help="Disk usage %% that triggers a warning (default: 90)")
    parser.add_argument("--interval", type=float, default=5.0,
                         help="Seconds between checks (default: 5)")
    parser.add_argument("--live", action="store_true",
                         help="Actually kill processes (default is dry-run/log-only)")
    parser.add_argument("--report-url", type=str, default=None,
                         help="URL of main agent's /report endpoint, e.g. "
                              "http://192.168.1.10:5000/report")
    parser.add_argument("--agent-id", type=str, default=None,
                         help="Unique ID for this sub-agent (default: this machine's hostname)")
    args = parser.parse_args()
    agent_id = args.agent_id or socket.gethostname()

    setup_logging()
    dry_run = not args.live
    own_pid = psutil.Process().pid

    logging.info("Starting monitor agent.")
    logging.info(f"CPU threshold: {args.cpu_threshold}% | RAM threshold: {args.ram_threshold}% | "
                 f"Disk threshold: {args.disk_threshold}%")
    logging.info(f"Mode: {'LIVE (will kill processes)' if not dry_run else 'DRY RUN (logging only)'}")

    last_kill_time_cpu = 0
    last_kill_time_ram = 0

    try:
        while True:
            cpu = psutil.cpu_percent(interval=1)
            ram = get_ram_usage()
            disk = get_disk_usage("/")

            logging.info(f"CPU: {cpu:.1f}% | RAM: {ram:.1f}% | Disk: {disk:.1f}%")

            last_action = "OK"

            if disk >= args.disk_threshold:
                logging.warning(f"Disk usage high: {disk:.1f}% >= {args.disk_threshold}%")
                last_action = f"Disk high ({disk:.1f}%)"

            if cpu >= args.cpu_threshold:
                now = time.time()
                if now - last_kill_time_cpu < COOLDOWN_SECONDS:
                    logging.info("CPU high, but still in cooldown period. Skipping action.")
                    last_action = "CPU high (cooldown)"
                else:
                    logging.warning(f"CPU usage high: {cpu:.1f}% >= {args.cpu_threshold}%")
                    proc, proc_cpu = get_top_cpu_process(exclude_pid=own_pid)

                    if proc is None:
                        logging.info("No suitable process found.")
                        last_action = "CPU high (no target)"
                    elif is_protected(proc):
                        logging.info(f"Top CPU process '{proc.name()}' is protected. Not killing.")
                        last_action = f"CPU high (protected: {proc.name()})"
                    else:
                        logging.info(f"Top CPU consumer: {proc.name()} (PID {proc.pid}) at {proc_cpu:.1f}%")
                        kill_process(proc, dry_run)
                        last_kill_time_cpu = now
                        verb = "Would kill" if dry_run else "Killed"
                        last_action = f"{verb} {proc.name()} (PID {proc.pid}) - high CPU"

            if ram >= args.ram_threshold:
                now = time.time()
                if now - last_kill_time_ram < COOLDOWN_SECONDS:
                    logging.info("RAM high, but still in cooldown period. Skipping action.")
                    last_action = "RAM high (cooldown)"
                else:
                    logging.warning(f"RAM usage high: {ram:.1f}% >= {args.ram_threshold}%")
                    proc, proc_ram = get_top_ram_process(exclude_pid=own_pid)

                    if proc is None:
                        logging.info("No suitable process found.")
                        last_action = "RAM high (no target)"
                    elif is_protected(proc):
                        logging.info(f"Top RAM process '{proc.name()}' is protected. Not killing.")
                        last_action = f"RAM high (protected: {proc.name()})"
                    else:
                        logging.info(f"Top RAM consumer: {proc.name()} (PID {proc.pid}) at {proc_ram:.1f}%")
                        kill_process(proc, dry_run)
                        last_kill_time_ram = now
                        verb = "Would kill" if dry_run else "Killed"
                        last_action = f"{verb} {proc.name()} (PID {proc.pid}) - high RAM"

            report_to_main_agent(args.report_url, agent_id, cpu, ram, disk, last_action)

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logging.info("Monitor agent stopped by user.")


if __name__ == "__main__":
    main()