import psutil
import time
import argparse
import logging
from datetime import datetime

PROTECTED_PROCESSES = {
    "systemd", "kernel_task", "launchd", "init", 
    "explorer.exe", "winlogon.exe", "csrss.exe", "services.exe",
    "python", "python3",
    "sshd", "bash", "zsh", "cmd.exe", "powershell.exe" ,
    "System",
"Registry",
"smss.exe",
"dwm.exe",
"lsass.exe"
}
COOLDOWN_SECONDS = 30

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler("monitor_agent.log"),
                  logging.StreamHandler(),
        ],
    )

def get_disk_usage(path="C:\\"):
    usage = psutil.disk_usage(path)
    return usage.percent

def get_top_cpu_process(exclude_pid=None):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            if p.info["pid"] == exclude_pid:
                continue
            procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    for p in procs:
        try:
            p.cpu_percent(interval = None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    time.sleep(0.5)

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

def is_protected(proc):
    try:
        name = proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return True
    return name in PROTECTED_PROCESSES

def kill_process(proc, dry_run):
    try:
        name = proc.name()
        pid = proc.pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return

    if dry_run:
        logging.info(f"[DRY RUN] would kill process: {name} (PID {pid})")
        return 

    try:
        proc.terminate()
        proc.wait(timeout=3)
        logging.warning(f"killed process: {name} (PID {pid})")
    except psutil.TimeoutExpired:
        proc.kill()
        logging.warning(f"killed process (force): {name} (PID {pid})")  
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logging.error(f"Failed to kill process: {name} (PID {pid}) - {e}")  

def main():
    parser = argparse.ArgumentParser(description="Simple CPU/Disk Monitor agent")
    parser.add_argument("--cpu-threshold", type=float, default=85.0, help="CPU usage %% that triggers action (default: 85)")
    parser.add_argument("--disk-threshold", type=float, default=90.0, help="Disk usage %% that triggers action (default: 90)")
    parser.add_argument("--interval", type=float, default=5.0, help="seconds between checks (default: 5)")
    parser.add_argument("--live", action="store_true", help="actually kill processes instead of dry run")
    args = parser.parse_args()

    setup_logging()
    dry_run = not args.live
    own_pid = psutil.Process().pid

    logging.info(f"Starting monitor agent with CPU threshold {args.cpu_threshold}%, Disk threshold {args.disk_threshold}%, interval {args.interval}s, dry_run={dry_run}")
    logging.info(f"mode : {'LIVE (will kill processes)' if not dry_run else 'DRY RUN (logging only)'}")

    last_kill_time = 0

    try:
        while True:
            cpu = psutil.cpu_percent(interval=1)
            disk = get_disk_usage("/")

            logging.info(f"CPU usage: {cpu:.2f}%, Disk usage: {disk:.2f}%")

            if disk >= args .disk_threshold:
                logging.warning(f"Disk usage {disk:.2f}% exceeds threshold {args.disk_threshold}%. Consider cleaning up disk space.")
            if cpu >= args.cpu_threshold:
                now = time.time()
                if now - last_kill_time < COOLDOWN_SECONDS:
                    logging.info(f"CPU usage {cpu:.2f}% exceeds threshold {args.cpu_threshold}%, but in cooldown period. Skipping kill.")
                else:
                    proc, proc_cpu = get_top_cpu_process(exclude_pid=own_pid)
                    if proc is None:
                        logging.warning("No process found to kill.")
                    elif is_protected(proc):
                        logging.warning(f"Top CPU process {proc.name()} (PID {proc.pid}) is protected. Skipping kill.")
                    else:
                        logging.warning(f"CPU usage {cpu:.2f}% exceeds threshold {args.cpu_threshold}%. Attempting to kill process {proc.name()} (PID {proc.pid}) using {proc_cpu:.2f}% CPU.")
                        kill_process(proc, dry_run)
                        last_kill_time = now
            time.sleep(args.interval)
    except KeyboardInterrupt:
        logging.info("Monitor agent stopped by user.")

if __name__ == "__main__":
    main()