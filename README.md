# Monitor Agent

A system monitoring agent for Windows that tracks CPU and disk usage, with automated process management to prevent resource exhaustion.

## Features

- **CPU Monitoring**: Tracks CPU usage with configurable thresholds
- **Disk Monitoring**: Monitors disk space usage
- **Automatic Process Termination**: Automatically kills high CPU-consuming processes (when enabled)
- **Protected Processes**: Safeguards critical system processes from termination
- **Dry-Run Mode**: Test process termination logic without actually killing processes
- **Configurable Thresholds**: Customize CPU and disk usage limits
- **Logging**: Comprehensive logging to both file (`monitor_agent.log`) and console

## Requirements

### Monitor Agent
- Python 3.x
- `psutil` library

### Main Agent
- Python 3.x
- `flask` library

## Installation

1. Install the monitor agent dependency:
```bash
pip install psutil
```

2. Install the main agent dependency:
```bash
pip install flask
```

## Running Both Agents

Start the main agent first:
```bash
python main_agent.py --port 5000
```

Then start the monitor agent and point it to the main agent:
```bash
python monitor_agent.py --report-url http://127.0.0.1:5000/report --agent-id my-agent
```

You can view the dashboard at:
```text
http://127.0.0.1:5000/dashboard
```

## Usage

### Basic Usage

Run the monitor agent with default settings:
```bash
python monitor_agent.py
```

### Command-Line Options

```bash
python monitor_agent.py [OPTIONS]
```

**Available options:**
- `--cpu-threshold PERCENTAGE` - CPU usage percentage that triggers action (default: 85%)
- `--disk-threshold PERCENTAGE` - Disk usage percentage that triggers action (default: 90%)
- `--interval SECONDS` - Seconds between system checks (default: 5)
- `--live` - Actually terminate processes (without this flag, runs in dry-run mode)

### Examples

**Dry-run mode (default - no processes are killed):**
```bash
python monitor_agent.py --cpu-threshold 80 --interval 10
```

**Live mode (actually terminates processes):**
```bash
python monitor_agent.py --cpu-threshold 80 --live
```

**Custom thresholds:**
```bash
python monitor_agent.py --cpu-threshold 75 --disk-threshold 85 --interval 5 --live
```

## Protected Processes

The following processes are protected and will not be terminated:
- System critical: `systemd`, `kernel_task`, `launchd`, `init`
- Windows services: `explorer.exe`, `winlogon.exe`, `csrss.exe`, `services.exe`, `System`, `Registry`, `smss.exe`, `dwm.exe`, `lsass.exe`
- Python interpreters: `python`, `python3`
- Shells: `sshd`, `bash`, `zsh`, `cmd.exe`, `powershell.exe`

## Output

Logs are written to `monitor_agent.log` with timestamps and severity levels. Example output:
```
2026-07-22 10:30:45 [INFO] Starting monitor agent...
2026-07-22 10:30:50 [WARNING] killed process: chrome.exe (PID 2048)
```

## Utility Scripts

### list-process.py

A simple utility script for checking disk usage:
```bash
python list-process.py
```

## Advanced Features

The Monitor Agent can be enhanced with the following integrations and features:

### Email Alerts
- Automatic email notifications when CPU or disk thresholds are exceeded
- Configurable recipient list and notification frequency
- Detailed alert messages with system metrics and affected processes

### Slack/Teams Notifications
- Real-time alerts to Slack or Microsoft Teams channels
- Custom message formatting with severity levels
- Process termination notifications with before/after metrics
- Integration with incident management workflows

### CloudWatch Integration
- Send system metrics to AWS CloudWatch
- Create custom alarms based on CPU and disk thresholds
- Enable centralized monitoring across multiple systems
- Integration with CloudWatch dashboards and alert policies

### Docker Container Deployment
- Containerized deployment for consistent environments
- Pre-configured Docker image with all dependencies
- Easy scaling and orchestration with Kubernetes
- Simplified CI/CD pipeline integration

### Metrics Dashboard (Grafana)
- Visual metrics dashboard using Grafana
- Real-time CPU and disk usage graphs
- Historical trend analysis and alerting
- Custom dashboard layouts and data source integration
- Process-level performance metrics

### Systemd Service Deployment
- Native systemd unit file for Linux systems
- Automatic startup on system boot
- Service management with systemctl commands
- Log rotation and journald integration
- Service restart policies and dependency management

## Notes

- Without the `--live` flag, all actions are simulated (dry-run mode)
- The agent has a 30-second cooldown between termination actions
- Graceful termination is attempted first; force kill is used if timeout occurs
- Run with administrator privileges for optimal functionality
