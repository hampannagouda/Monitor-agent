# Monitor Agent

This workspace contains a small monitoring setup for Windows that combines a local system monitor with a lightweight Flask-based status dashboard.

## What is included

- main_agent.py: a Flask service that collects status updates from monitor agents and serves a simple dashboard
- monitor_agent.py: a sub-agent that checks CPU, RAM, and disk usage and can optionally terminate high-resource processes
- list-process.py: a simple utility script for inspecting disk usage
- app.py: a minimal Flask example app

## Features

- CPU, RAM, and disk monitoring
- Optional automatic process termination in live mode
- Protected process handling to avoid killing essential system processes
- Dry-run mode by default for safe testing
- Logging to both the console and log files
- A basic dashboard for viewing agent status

## Requirements

Install the Python dependencies:

```bash
pip install psutil flask
```

## Running the main agent

Start the central Flask service first:

```bash
python main_agent.py --port 5000
```

Then open:

```text
http://127.0.0.1:5000/dashboard
```

## Running the monitor agent

Start a monitor agent and send reports to the main agent:

```bash
python monitor_agent.py --report-url http://127.0.0.1:5000/report --agent-id my-agent
```

### Common options

```bash
python monitor_agent.py [OPTIONS]
```

Available options:
- --cpu-threshold PERCENTAGE: CPU usage threshold that triggers action (default: 85)
- --ram-threshold PERCENTAGE: RAM usage threshold that triggers action (default: 85)
- --disk-threshold PERCENTAGE: Disk usage threshold that triggers a warning (default: 90)
- --interval SECONDS: Delay between checks (default: 5)
- --live: Enable actual process termination (default is dry-run)
- --report-url URL: Main agent /report endpoint
- --agent-id ID: Unique name for this sub-agent

### Examples

Dry-run mode (default):

```bash
python monitor_agent.py
```

Live mode:

```bash
python monitor_agent.py --live
```

Custom thresholds:

```bash
python monitor_agent.py --cpu-threshold 80 --ram-threshold 85 --interval 5 --live
```

## Main agent endpoints

- POST /report: accepts JSON status updates from sub-agents
- GET /status: returns the current agent snapshot as JSON
- GET /dashboard: displays a simple browser-based dashboard

## Notes

- By default, monitor_agent.py runs in dry-run mode and only logs what it would do.
- Critical or essential processes are protected and will not be terminated.
- For the best experience on Windows, run the scripts with administrator privileges.
- Logs are written to monitor_agent.log and main_agent.log.
