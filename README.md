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

- Python 3.x
- `psutil` library

## Installation

1. Install dependencies:
```bash
pip install psutil
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

## Notes

- Without the `--live` flag, all actions are simulated (dry-run mode)
- The agent has a 30-second cooldown between termination actions
- Graceful termination is attempted first; force kill is used if timeout occurs
- Run with administrator privileges for optimal functionality
